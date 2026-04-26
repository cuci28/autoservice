from flask import Blueprint, current_app, render_template
from sqlalchemy import desc, func, select

from .extensions import db
from .service_layer import fetch_order_receipt

# Blueprint для веб-интерфейса на HTML-шаблонах.
ui = Blueprint('ui', __name__)


def get_tables():
    """Возвращает отраженные таблицы, подготовленные при старте приложения."""
    return current_app.extensions['autoservice_tables']


def load_dashboard_stats(tables):
    """Собирает компактную статистику для главной страницы."""
    return {
        'clients': db.session.execute(select(func.count()).select_from(tables['clients'])).scalar_one(),
        'cars': db.session.execute(select(func.count()).select_from(tables['cars'])).scalar_one(),
        'orders': db.session.execute(select(func.count()).select_from(tables['orders'])).scalar_one(),
        'masters': db.session.execute(select(func.count()).select_from(tables['masters'])).scalar_one(),
        'parts': db.session.execute(select(func.count()).select_from(tables['warehouse'])).scalar_one(),
    }


@ui.route('/')
def dashboard():
    """Главная страница веб-интерфейса."""
    tables = get_tables()
    stats = load_dashboard_stats(tables)

    recent_orders = db.session.execute(
        select(
            tables['orders'].c.order_id,
            tables['orders'].c.order_date,
            tables['orders'].c.status,
            tables['orders'].c.total_cost,
            tables['cars'].c.car_model,
            tables['clients'].c.full_name,
            tables['masters'].c.master_name,
        )
        .select_from(
            tables['orders']
            .join(tables['cars'], tables['orders'].c.car_id == tables['cars'].c.car_id)
            .join(tables['clients'], tables['cars'].c.client_id == tables['clients'].c.client_id)
            .outerjoin(tables['masters'], tables['orders'].c.master_id == tables['masters'].c.master_id)
        )
        .order_by(desc(tables['orders'].c.order_id))
        .limit(6)
    ).mappings().all()

    return render_template('dashboard.html', stats=stats, recent_orders=recent_orders)


@ui.route('/clients')
def clients_page():
    """Страница клиентов и машин."""
    tables = get_tables()
    clients = db.session.execute(
        select(tables['clients']).order_by(desc(tables['clients'].c.client_id))
    ).mappings().all()
    cars = db.session.execute(
        select(
            tables['cars'].c.car_id,
            tables['cars'].c.client_id,
            tables['cars'].c.car_model,
            tables['cars'].c.year,
            tables['cars'].c.vin,
            tables['clients'].c.full_name,
        )
        .select_from(tables['cars'].join(tables['clients'], tables['cars'].c.client_id == tables['clients'].c.client_id))
        .order_by(desc(tables['cars'].c.car_id))
    ).mappings().all()
    return render_template('clients.html', clients=clients, cars=cars)


@ui.route('/services')
def services_page():
    """Страница управления услугами."""
    tables = get_tables()
    services = db.session.execute(
        select(tables['services']).order_by(desc(tables['services'].c.service_id))
    ).mappings().all()
    return render_template('services.html', services=services)


@ui.route('/masters')
def masters_page():
    """Страница управления мастерами."""
    tables = get_tables()
    masters = db.session.execute(
        select(tables['masters']).order_by(desc(tables['masters'].c.master_id))
    ).mappings().all()
    return render_template('masters.html', masters=masters)


@ui.route('/warehouse')
def warehouse_page():
    """Страница склада и поступлений."""
    tables = get_tables()
    parts = db.session.execute(
        select(tables['warehouse']).order_by(tables['warehouse'].c.part_name)
    ).mappings().all()
    return render_template('warehouse.html', parts=parts)


@ui.route('/orders')
def orders_page():
    """Страница списка заказов."""
    tables = get_tables()
    orders = db.session.execute(
        select(
            tables['orders'].c.order_id,
            tables['orders'].c.order_date,
            tables['orders'].c.status,
            tables['orders'].c.total_cost,
            tables['cars'].c.car_model,
            tables['clients'].c.full_name,
            tables['masters'].c.master_name,
        )
        .select_from(
            tables['orders']
            .join(tables['cars'], tables['orders'].c.car_id == tables['cars'].c.car_id)
            .join(tables['clients'], tables['cars'].c.client_id == tables['clients'].c.client_id)
            .outerjoin(tables['masters'], tables['orders'].c.master_id == tables['masters'].c.master_id)
        )
        .order_by(desc(tables['orders'].c.order_id))
    ).mappings().all()
    return render_template('orders.html', orders=orders)


@ui.route('/orders/new')
def new_order_page():
    """Страница создания заказа."""
    tables = get_tables()
    cars = db.session.execute(
        select(
            tables['cars'].c.car_id,
            tables['cars'].c.car_model,
            tables['cars'].c.year,
            tables['cars'].c.vin,
            tables['clients'].c.full_name,
        )
        .select_from(tables['cars'].join(tables['clients'], tables['cars'].c.client_id == tables['clients'].c.client_id))
        .order_by(tables['cars'].c.car_id)
    ).mappings().all()
    masters = db.session.execute(
        select(tables['masters']).order_by(tables['masters'].c.master_name)
    ).mappings().all()
    services = db.session.execute(
        select(tables['services']).order_by(tables['services'].c.service_name)
    ).mappings().all()
    parts = db.session.execute(
        select(tables['warehouse']).order_by(tables['warehouse'].c.part_name)
    ).mappings().all()
    return render_template('order_new.html', cars=cars, masters=masters, services=services, parts=parts)


@ui.route('/orders/<int:order_id>/receipt')
def receipt_page(order_id):
    """Страница печатного чека заказа."""
    receipt = fetch_order_receipt(get_tables(), order_id)
    if not receipt:
        return render_template('receipt.html', receipt=None, order_id=order_id), 404
    return render_template('receipt.html', receipt=receipt, order_id=order_id)
