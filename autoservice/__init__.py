from pathlib import Path

from flask import Flask

from .api import api
from .extensions import db
from .store import init_tables
from .ui import ui


def create_app():
    """Фабрика Flask-приложения: конфиг, БД, таблицы и маршруты."""
    project_root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=str(project_root / 'templates'),
        static_folder=str(project_root / 'static'),
    )

    # Явно указываем БД в корне проекта
    db_path = project_root / 'autoservice.db'
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
    # Регистрируем веб-интерфейс на HTML-шаблонах.
    app.register_blueprint(ui)
    return app
