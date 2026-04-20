from pathlib import Path

from flask import Flask

from .api import api
from .extensions import db
from .store import init_tables


def create_app():
    """Фабрика Flask-приложения: конфиг, БД, таблицы и маршруты."""
    app = Flask(__name__)

    # Явно указываем БД в корне проекта
    db_path = Path(__file__).resolve().parent.parent / 'autoservice.db'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path.as_posix()}'
    # Отключаем лишние сигналы отслеживания изменений объектов.
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Подключаем SQLAlchemy к текущему приложению.
    db.init_app(app)

    # Загружаем таблицы из существующей БД и сохраняем ссылки в extensions.
    with app.app_context():
        app.extensions['autoservice_tables'] = init_tables()

    # Регистрируем все API-роуты.
    app.register_blueprint(api)
    return app
