from sqlalchemy import func, insert, select, update

from .extensions import db


def require_fields(payload, fields):
    """Проверяет, что в JSON есть все обязательные поля."""
    # Если поле отсутствует или пустое, возвращаем ошибку для API-ответа.
    missing = [field for field in fields if not payload.get(field)]
    if missing:
        return False, {'error': f"Отсутствуют поля: {', '.join(missing)}"}
    return True, None


def ensure_car_exists(tables, car_id):
    """Проверяет существование машины по идентификатору."""
    car_exists = db.session.execute(
        select(tables['cars'].c.car_id).where(tables['cars'].c.car_id == car_id)
    ).first()
    return car_exists is not None


def ensure_master_exists(tables, master_id):
    """Проверяет существование мастера. None допустим для неназначенного заказа."""
    if master_id is None:
        return True
    master_exists = db.session.execute(
        select(tables['masters'].c.master_id).where(tables['masters'].c.master_id == master_id)
    ).first()
    return master_exists is not None


def ensure_stock_available(tables, parts_payload):
    """Проверяет, что все запчасти существуют и их достаточно на складе."""
    warehouse = tables['warehouse']
    for item in parts_payload:
        # Для каждой позиции заказа читаем актуальный остаток со склада.
        part_row = db.session.execute(
            select(warehouse.c.part_id, warehouse.c.stock_quantity)
            .where(warehouse.c.part_id == item['part_id'])
        ).mappings().first()

        if not part_row:
            return False, f"Запчасть id={item['part_id']} не найдена"

        if int(item['quantity']) <= 0:
            return False, f"Количество для part_id={item['part_id']} должно быть больше нуля"

        if part_row['stock_quantity'] < int(item['quantity']):
            return False, f"Недостаточно запаса для part_id={item['part_id']}"

    return True, None


def recalculate_order_total(tables, order_id):
    """Пересчитывает стоимость заказа как сумму услуг и запчастей."""
    order_services = tables['order_services']
    order_parts = tables['order_parts']
    warehouse = tables['warehouse']
    orders = tables['orders']

    # Сумма услуг берется из сохраненной цены услуги на момент добавления в заказ.
    services_total = db.session.execute(
        select(func.coalesce(func.sum(order_services.c.quantity * order_services.c.price_at_time), 0)).where(
            order_services.c.order_id == order_id
        )
    ).scalar_one()

    # Сумма запчастей считается по текущей цене запчасти из склада.
    parts_total = db.session.execute(
        select(func.coalesce(func.sum(order_parts.c.quantity * warehouse.c.unit_price), 0))
        .select_from(order_parts.join(warehouse, order_parts.c.part_id == warehouse.c.part_id))
        .where(order_parts.c.order_id == order_id)
    ).scalar_one()

    # Обновляем total_cost прямо в таблице заказов.
    total = int(services_total + parts_total)
    db.session.execute(
        update(orders).where(orders.c.order_id == order_id).values(total_cost=total)
    )
    return total


def fetch_order_receipt(tables, order_id):
    """Собирает данные чека: шапка заказа, услуги и запчасти."""
    orders = tables['orders']
    cars = tables['cars']
    clients = tables['clients']
    masters = tables['masters']
    order_services = tables['order_services']
    services = tables['services']
    order_parts = tables['order_parts']
    warehouse = tables['warehouse']

    # Блок "шапки" чека: клиент, машина, мастер, дата и итог.
    order_row = db.session.execute(
        select(
            orders.c.order_id,
            orders.c.order_date,
            orders.c.status,
            orders.c.total_cost,
            cars.c.car_id,
            cars.c.car_model,
            cars.c.vin,
            clients.c.client_id,
            clients.c.full_name,
            clients.c.phone_number,
            masters.c.master_id,
            masters.c.master_name,
        )
        .select_from(
            orders.join(cars, orders.c.car_id == cars.c.car_id)
            .join(clients, cars.c.client_id == clients.c.client_id)
            .outerjoin(masters, orders.c.master_id == masters.c.master_id)
        )
        .where(orders.c.order_id == order_id)
    ).mappings().first()

    if not order_row:
        return None

    # Позиции услуг в чеке.
    service_rows = db.session.execute(
        select(
            order_services.c.service_id,
            services.c.service_name,
            order_services.c.quantity,
            order_services.c.price_at_time,
            (order_services.c.quantity * order_services.c.price_at_time).label('line_total'),
        )
        .select_from(order_services.join(services, order_services.c.service_id == services.c.service_id))
        .where(order_services.c.order_id == order_id)
    ).mappings().all()

    # Позиции запчастей в чеке.
    part_rows = db.session.execute(
        select(
            order_parts.c.part_id,
            warehouse.c.part_name,
            order_parts.c.quantity,
            warehouse.c.unit_price,
            (order_parts.c.quantity * warehouse.c.unit_price).label('line_total'),
        )
        .select_from(order_parts.join(warehouse, order_parts.c.part_id == warehouse.c.part_id))
        .where(order_parts.c.order_id == order_id)
    ).mappings().all()

    return {
        'order': dict(order_row),
        'services': [dict(row) for row in service_rows],
        'parts': [dict(row) for row in part_rows],
    }


def add_services_to_order(tables, order_id, services_payload):
    """Добавляет услуги в заказ и фиксирует цену услуги на момент добавления."""
    services = tables['services']
    order_services = tables['order_services']

    for service_item in services_payload:
        # Проверяем корректность услуги и количества перед вставкой.
        service_id = service_item.get('service_id')
        quantity = int(service_item.get('quantity', 1))
        service_row = db.session.execute(
            select(services.c.service_id, services.c.price).where(services.c.service_id == service_id)
        ).mappings().first()
        if not service_row:
            raise ValueError(f'Услуга id={service_id} не найдена')
        if quantity <= 0:
            raise ValueError(f'Количество для service_id={service_id} должно быть больше нуля')

        db.session.execute(
            insert(order_services).values(
                order_id=order_id,
                service_id=service_id,
                quantity=quantity,
                price_at_time=service_row['price'],
            )
        )


def add_parts_to_order(tables, order_id, parts_payload):
    """Добавляет запчасти в заказ. Остаток уменьшается триггером в БД."""
    order_parts = tables['order_parts']
    for part_item in parts_payload:
        db.session.execute(
            insert(order_parts).values(
                order_id=order_id,
                part_id=part_item['part_id'],
                quantity=int(part_item['quantity']),
            )
        )


def restore_order_parts_stock(tables, order_id):
    """Возвращает на склад все запчасти, списанные в заказе."""
    order_parts = tables['order_parts']
    warehouse = tables['warehouse']

    rows = db.session.execute(
        select(
            order_parts.c.part_id,
            func.sum(order_parts.c.quantity).label('quantity_sum'),
        )
        .where(order_parts.c.order_id == order_id)
        .group_by(order_parts.c.part_id)
    ).mappings().all()

    for row in rows:
        db.session.execute(
            update(warehouse)
            .where(warehouse.c.part_id == row['part_id'])
            .values(stock_quantity=warehouse.c.stock_quantity + int(row['quantity_sum']))
        )
