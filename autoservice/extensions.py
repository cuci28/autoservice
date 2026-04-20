from flask_sqlalchemy import SQLAlchemy

# Единый экземпляр SQLAlchemy для всего приложения.
# Импортируется в других модулях, чтобы все работали с одной сессией БД.
db = SQLAlchemy()
