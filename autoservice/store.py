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
