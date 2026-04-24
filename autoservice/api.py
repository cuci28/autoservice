from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError

from .extensions import db
from .service_layer import (
    add_parts_to_order,
    add_services_to_order,
    ensure_car_exists,
    ensure_master_exists,
    ensure_stock_available,
    fetch_order_receipt,
    recalculate_order_total,
    require_fields,
)

# BluePrint объединяет все HTTP-маршруты backend API.
api = Blueprint('api', __name__)


def get_tables():
    """Возвращает словарь отраженных таблиц, сохраненный при старте приложения."""
    return current_app.extensions['autoservice_tables']


@api.route('/api')
def index():
    """Служебный маршрут: проверка доступности API и список основных endpoint'ов."""
    return jsonify(
        {
            'message': 'API автосервиса работает',
            'docs': {
                'create_client_with_car': 'POST /api/clients-with-car',
                'create_order': 'POST /api/orders',
                'add_order_items': 'POST /api/orders/<order_id>/items',
                'get_receipt': 'GET /api/orders/<order_id>/receipt',
                'masters': 'GET/POST/DELETE /api/masters',
                'assign_master': 'PATCH /api/orders/<order_id>/master',
                'warehouse_income': 'POST /api/warehouse/incoming',
            },
        }
    )


@api.route('/api/clients-with-car', methods=['POST'])
def create_client_with_car():
    """Создает клиента и сразу привязанную к нему машину в одной транзакции."""
    tables = get_tables()
    payload = request.get_json(silent=True) or {}
    car_payload = payload.get('car') or {}

    ok, error = require_fields(payload, ['full_name', 'phone_number'])
    if not ok:
        return jsonify(error), 400

    ok, error = require_fields(car_payload, ['car_model', 'year', 'vin'])
    if not ok:
        return jsonify({'error': f"Неверные данные машины. {error['error']}"}), 400

    try:
        with db.session.begin():
            client_result = db.session.execute(
                insert(tables['clients']).values(
                    full_name=payload['full_name'],
                    phone_number=payload['phone_number'],
                    email=payload.get('email'),
                )
            )
            client_id = client_result.inserted_primary_key[0]

            car_result = db.session.execute(
                insert(tables['cars']).values(
                    client_id=client_id,
                    car_model=car_payload['car_model'],
                    year=car_payload['year'],
                    vin=car_payload['vin'],
                )
            )
            car_id = car_result.inserted_primary_key[0]
    except IntegrityError as ex:
        db.session.rollback()
        return jsonify({'error': 'Нарушение ограничений БД', 'details': str(ex.orig)}), 400

    return jsonify({'client_id': client_id, 'car_id': car_id}), 201


@api.route('/api/masters', methods=['GET'])
def list_masters():
    """Возвращает список всех мастеров."""
    tables = get_tables()
    rows = db.session.execute(select(tables['masters'])).mappings().all()
    return jsonify([dict(row) for row in rows])


@api.route('/api/masters', methods=['POST'])
def create_master():
    """Добавляет нового мастера."""
    tables = get_tables()
    payload = request.get_json(silent=True) or {}
    ok, error = require_fields(payload, ['master_name', 'phone_number'])
    if not ok:
        return jsonify(error), 400

    try:
        with db.session.begin():
            result = db.session.execute(
                insert(tables['masters']).values(
                    master_name=payload['master_name'],
                    phone_number=payload['phone_number'],
                    email=payload.get('email'),
                )
            )
            master_id = result.inserted_primary_key[0]
    except IntegrityError as ex:
        db.session.rollback()
        return jsonify({'error': 'Нарушение ограничений БД', 'details': str(ex.orig)}), 400

    return jsonify({'master_id': master_id}), 201


@api.route('/api/masters/<int:master_id>', methods=['DELETE'])
def delete_master(master_id):
    """Удаляет мастера по id."""
    tables = get_tables()
    try:
        with db.session.begin():
            result = db.session.execute(
                delete(tables['masters']).where(tables['masters'].c.master_id == master_id)
            )
    except IntegrityError as ex:
        db.session.rollback()
        return jsonify({'error': 'Нельзя удалить мастера', 'details': str(ex.orig)}), 400

    if result.rowcount == 0:
        return jsonify({'error': 'Мастер не найден'}), 404

    return jsonify({'message': 'Мастер удален'})


@api.route('/api/orders', methods=['POST'])
def create_order():
    """Создает заказ, добавляет позиции и пересчитывает итоговую стоимость."""
    tables = get_tables()
    payload = request.get_json(silent=True) or {}
    services_payload = payload.get('services', [])
    parts_payload = payload.get('parts', [])

    ok, error = require_fields(payload, ['car_id'])
    if not ok:
        return jsonify(error), 400

    if not ensure_car_exists(tables, payload['car_id']):
        return jsonify({'error': 'Машина не найдена'}), 404

    master_id = payload.get('master_id')
    if not ensure_master_exists(tables, master_id):
        return jsonify({'error': 'Мастер не найден'}), 404

    stock_ok, stock_error = ensure_stock_available(tables, parts_payload)
    if not stock_ok:
        return jsonify({'error': stock_error}), 400

    try:
        # Все операции по заказу выполняются атомарно.
        with db.session.begin():
            order_result = db.session.execute(
                insert(tables['orders']).values(
                    car_id=payload['car_id'],
                    status=payload.get('status', 'в работе'),
                    master_id=master_id,
                )
            )
            order_id = order_result.inserted_primary_key[0]

            add_services_to_order(tables, order_id, services_payload)
            add_parts_to_order(tables, order_id, parts_payload)
            total = recalculate_order_total(tables, order_id)
    except ValueError as ex:
        db.session.rollback()
        return jsonify({'error': str(ex)}), 400
    except IntegrityError as ex:
        db.session.rollback()
        return jsonify({'error': 'Нарушение ограничений БД', 'details': str(ex.orig)}), 400

    return jsonify({'order_id': order_id, 'total_cost': total}), 201


@api.route('/api/orders/<int:order_id>/items', methods=['POST'])
def add_items_to_order(order_id):
    """Добавляет услуги и запчасти в уже существующий заказ."""
    tables = get_tables()
    payload = request.get_json(silent=True) or {}
    services_payload = payload.get('services', [])
    parts_payload = payload.get('parts', [])

    order_exists = db.session.execute(
        select(tables['orders'].c.order_id).where(tables['orders'].c.order_id == order_id)
    ).first()
    if not order_exists:
        return jsonify({'error': 'Заказ не найден'}), 404

    stock_ok, stock_error = ensure_stock_available(tables, parts_payload)
    if not stock_ok:
        return jsonify({'error': stock_error}), 400

    try:
        # После добавления позиций всегда обновляем total_cost.
        with db.session.begin():
            add_services_to_order(tables, order_id, services_payload)
            add_parts_to_order(tables, order_id, parts_payload)
            total = recalculate_order_total(tables, order_id)
    except ValueError as ex:
        db.session.rollback()
        return jsonify({'error': str(ex)}), 400
    except IntegrityError as ex:
        db.session.rollback()
        return jsonify({'error': 'Нарушение ограничений БД', 'details': str(ex.orig)}), 400

    return jsonify({'message': 'Позиции добавлены', 'total_cost': total})


@api.route('/api/orders/<int:order_id>/master', methods=['PATCH'])
def assign_master(order_id):
    """Назначает мастера на заказ."""
    tables = get_tables()
    payload = request.get_json(silent=True) or {}
    master_id = payload.get('master_id')

    if master_id is None:
        return jsonify({'error': 'Нужно передать master_id'}), 400

    if not ensure_master_exists(tables, master_id):
        return jsonify({'error': 'Мастер не найден'}), 404

    with db.session.begin():
        result = db.session.execute(
            update(tables['orders'])
            .where(tables['orders'].c.order_id == order_id)
            .values(master_id=master_id)
        )

    if result.rowcount == 0:
        return jsonify({'error': 'Заказ не найден'}), 404

    return jsonify({'message': 'Мастер назначен'})


@api.route('/api/orders/<int:order_id>/receipt', methods=['GET'])
def get_order_receipt(order_id):
    """Возвращает чек по заказу со всеми позициями."""
    receipt = fetch_order_receipt(get_tables(), order_id)
    if not receipt:
        return jsonify({'error': 'Заказ не найден'}), 404
    return jsonify(receipt)


@api.route('/api/warehouse/incoming', methods=['POST'])
def add_warehouse_income():
    """Учитывает поступление запчастей на склад (увеличивает остаток)."""
    tables = get_tables()
    payload = request.get_json(silent=True) or {}
    ok, error = require_fields(payload, ['part_id', 'quantity'])
    if not ok:
        return jsonify(error), 400

    quantity = int(payload['quantity'])
    if quantity <= 0:
        return jsonify({'error': 'Количество должно быть больше нуля'}), 400

    with db.session.begin():
        result = db.session.execute(
            update(tables['warehouse'])
            .where(tables['warehouse'].c.part_id == payload['part_id'])
            .values(stock_quantity=tables['warehouse'].c.stock_quantity + quantity)
        )

    if result.rowcount == 0:
        return jsonify({'error': 'Запчасть не найдена'}), 404

    return jsonify({'message': 'Поступление учтено'})


@api.route('/api/warehouse/writeoff', methods=['POST'])
def writeoff_warehouse_part():
    """Списывает запчасти со склада с проверкой остатка."""
    tables = get_tables()
    payload = request.get_json(silent=True) or {}
    ok, error = require_fields(payload, ['part_id', 'quantity'])
    if not ok:
        return jsonify(error), 400

    quantity = int(payload['quantity'])
    if quantity <= 0:
        return jsonify({'error': 'Количество должно быть больше нуля'}), 400

    part_row = db.session.execute(
        select(
            tables['warehouse'].c.part_id,
            tables['warehouse'].c.stock_quantity,
        ).where(tables['warehouse'].c.part_id == payload['part_id'])
    ).mappings().first()

    if not part_row:
        return jsonify({'error': 'Запчасть не найдена'}), 404

    if part_row['stock_quantity'] < quantity:
        return jsonify({'error': 'Недостаточно запчастей на складе для списания'}), 400

    with db.session.begin():
        db.session.execute(
            update(tables['warehouse'])
            .where(tables['warehouse'].c.part_id == payload['part_id'])
            .values(stock_quantity=tables['warehouse'].c.stock_quantity - quantity)
        )

    return jsonify({'message': 'Списание выполнено'})


@api.route('/api/warehouse/parts', methods=['GET', 'POST'])
def list_parts():
    """Возвращает список запчастей или добавляет новую позицию на склад."""
    tables = get_tables()

    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
        ok, error = require_fields(payload, ['part_name', 'unit_price'])
        if not ok:
            return jsonify(error), 400

        try:
            stock_quantity = int(payload.get('stock_quantity', 0))
            unit_price = int(payload['unit_price'])
        except (TypeError, ValueError):
            return jsonify({'error': 'Количество и цена должны быть числами'}), 400

        if stock_quantity < 0:
            return jsonify({'error': 'Начальный остаток не может быть отрицательным'}), 400
        if unit_price <= 0:
            return jsonify({'error': 'Цена должна быть больше нуля'}), 400

        try:
            with db.session.begin():
                result = db.session.execute(
                    insert(tables['warehouse']).values(
                        part_name=payload['part_name'].strip(),
                        stock_quantity=stock_quantity,
                        unit_price=unit_price,
                    )
                )
                part_id = result.inserted_primary_key[0]
        except IntegrityError as ex:
            db.session.rollback()
            return jsonify({'error': 'Нарушение ограничений БД', 'details': str(ex.orig)}), 400

        return jsonify({'message': 'Запчасть добавлена', 'part_id': part_id}), 201

    rows = db.session.execute(select(tables['warehouse'])).mappings().all()
    return jsonify([dict(row) for row in rows])


@api.route('/api/warehouse/parts/<int:part_id>', methods=['PATCH'])
def update_part(part_id):
    """Обновляет название и/или цену запчасти на складе."""
    tables = get_tables()
    payload = request.get_json(silent=True) or {}

    part_name = payload.get('part_name')
    unit_price = payload.get('unit_price')

    if part_name is None and unit_price is None:
        return jsonify({'error': 'Нужно передать part_name и/или unit_price'}), 400

    values_to_update = {}
    if part_name is not None:
        cleaned_name = str(part_name).strip()
        if not cleaned_name:
            return jsonify({'error': 'Название запчасти не может быть пустым'}), 400
        values_to_update['part_name'] = cleaned_name

    if unit_price is not None:
        try:
            parsed_price = int(unit_price)
        except (TypeError, ValueError):
            return jsonify({'error': 'Цена должна быть числом'}), 400
        if parsed_price <= 0:
            return jsonify({'error': 'Цена должна быть больше нуля'}), 400
        values_to_update['unit_price'] = parsed_price

    try:
        with db.session.begin():
            result = db.session.execute(
                update(tables['warehouse'])
                .where(tables['warehouse'].c.part_id == part_id)
                .values(**values_to_update)
            )
    except IntegrityError as ex:
        db.session.rollback()
        return jsonify({'error': 'Нарушение ограничений БД', 'details': str(ex.orig)}), 400

    if result.rowcount == 0:
        return jsonify({'error': 'Запчасть не найдена'}), 404

    return jsonify({'message': 'Запчасть обновлена'})


@api.route('/api/services', methods=['GET'])
def list_services():
    """Возвращает список услуг."""
    tables = get_tables()
    rows = db.session.execute(select(tables['services'])).mappings().all()
    return jsonify([dict(row) for row in rows])


@api.route('/api/cars', methods=['GET'])
def list_cars():
    """Возвращает список машин."""
    tables = get_tables()
    rows = db.session.execute(select(tables['cars'])).mappings().all()
    return jsonify([dict(row) for row in rows])


@api.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    """Возвращает карточку заказа по id без детализации позиций."""
    tables = get_tables()
    row = db.session.execute(
        select(tables['orders']).where(tables['orders'].c.order_id == order_id)
    ).mappings().first()
    if not row:
        return jsonify({'error': 'Заказ не найден'}), 404
    return jsonify(dict(row))
