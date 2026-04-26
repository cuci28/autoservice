from sqlalchemy import inspect, text

from .extensions import db

# Список таблиц, которые обязаны существовать в базе для корректной работы API.
REQUIRED_TABLES = {
    'clients',
    'cars',
    'services',
    'masters',
    'warehouse',
    'orders',
    'order_parts',
    'order_services',
}


def init_tables():
    """Отражает структуру БД и возвращает словарь таблиц по именам."""
    # Читаем схему существующей SQLite-базы.
    db.Model.metadata.reflect(bind=db.engine)
    metadata = db.Model.metadata

    # Проверяем, что все ожидаемые таблицы реально есть в базе.
    missing_tables = REQUIRED_TABLES - set(metadata.tables.keys())
    if missing_tables:
        raise RuntimeError(
            f"В базе отсутствуют таблицы: {', '.join(sorted(missing_tables))}"
        )

    # Возвращаем удобный словарь для дальнейшей работы в сервисах и роутерах.
    return {
        'clients': metadata.tables['clients'],
        'cars': metadata.tables['cars'],
        'services': metadata.tables['services'],
        'masters': metadata.tables['masters'],
        'warehouse': metadata.tables['warehouse'],
        'orders': metadata.tables['orders'],
        'order_parts': metadata.tables['order_parts'],
        'order_services': metadata.tables['order_services'],
    }


def ensure_order_parts_price_at_time_column():
    """Добавляет в order_parts колонку цены на момент заказа, если ее еще нет."""
    inspector = inspect(db.engine)
    columns = {column['name'] for column in inspector.get_columns('order_parts')}
    if 'price_at_time' in columns:
        return

    # Для старой базы добавляем колонку и заполняем ее текущей ценой запчасти.
    with db.engine.begin() as connection:
        connection.execute(
            text('ALTER TABLE order_parts ADD COLUMN price_at_time INTEGER NOT NULL DEFAULT 0')
        )
        connection.execute(
            text(
                'UPDATE order_parts '
                'SET price_at_time = COALESCE((SELECT unit_price FROM warehouse WHERE warehouse.part_id = order_parts.part_id), 0) '
                'WHERE price_at_time = 0'
            )
        )
