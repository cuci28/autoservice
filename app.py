# Точка входа: запускает Flask-приложение, собранное в пакете autoservice.
from autoservice import create_app

# Создаем экземпляр приложения через фабрику.
app = create_app()


if __name__ == '__main__':
    # Локальный запуск в режиме отладки для разработки.
    app.run(debug=True)