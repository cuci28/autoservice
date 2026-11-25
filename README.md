# AutoService

Веб-приложение для управления работой автосервиса: клиентами и их автомобилями, мастерами, услугами, складом и ремонтными заказами.

Проект написан на Python с использованием Flask и Flask-SQLAlchemy. В качестве базы данных используется SQLite.

## Возможности

- Панель управления с общей статистикой и последними заказами.
- Добавление и редактирование клиентов и автомобилей.
- Управление мастерами и назначение мастера на заказ.
- Справочник услуг с ценами.
- Учет запчастей: остатки, поступления и списания.
- Создание заказов с несколькими услугами и запчастями.
- Автоматический пересчет стоимости заказа.
- Изменение статуса заказа: «в работе», «завершен», «отменен».
- Возврат запчастей на склад при отмене заказа.
- Просмотр печатного чека заказа.
- REST API для интеграции с внешними системами.

## Технологии

- Python 3
- Flask
- Flask-SQLAlchemy
- SQLAlchemy
- SQLite
- HTML, CSS и JavaScript

## Структура проекта

```text
.
├── app.py                  # Точка входа приложения
├── autoservice/
│   ├── __init__.py         # Фабрика Flask-приложения
│   ├── api.py              # REST API-маршруты
│   ├── ui.py               # Маршруты веб-интерфейса
│   ├── store.py            # Проверка и отражение схемы SQLite
│   ├── service_layer.py    # Бизнес-логика заказов и склада
│   └── extensions.py       # Экземпляр SQLAlchemy
├── templates/              # HTML-шаблоны Jinja
├── static/                 # CSS и JavaScript
├── autoservice.db          # Основная база данных SQLite
├── requirements.txt        # Зависимости проекта
└── txt/                    # Примеры SQL-запросов и документационные материалы
```

## Установка и запуск

### 1. Создайте виртуальное окружение

Для Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Для Windows:

```powershell
py -m venv .venv
.venv\Scripts\activate
```

### 2. Установите зависимости

```bash
python -m pip install -r requirements.txt
```

### 3. Запустите приложение

```bash
python app.py
```

Приложение будет доступно по адресу [http://127.0.0.1:5000](http://127.0.0.1:5000).

Режим отладки включен при запуске через `app.py`.

## База данных

Приложение использует файл `autoservice.db` в корне проекта. При запуске оно автоматически отражает существующую SQLite-схему и проверяет наличие следующих таблиц:

- `clients`
- `cars`
- `services`
- `masters`
- `warehouse`
- `orders`
- `order_parts`
- `order_services`

Отдельное создание схемы при старте не выполняется: база должна содержать таблицы с ожидаемыми колонками.

## Веб-интерфейс

| Страница | Адрес |
| --- | --- |
| Панель управления | `/` |
| Клиенты и автомобили | `/clients` |
| Заказы | `/orders` |
| Новый заказ | `/orders/new` |
| Мастера | `/masters` |
| Услуги | `/services` |
| Склад | `/warehouse` |
| Информация об API | `/api` |
| Чек заказа | `/orders/<order_id>/receipt` |

## Основные REST API-маршруты

| Метод | Маршрут | Назначение |
| --- | --- | --- |
| `GET` | `/api` | Проверка доступности API |
| `POST` | `/api/clients-with-car` | Создание клиента вместе с автомобилем |
| `GET/PATCH/DELETE` | `/api/cars/<car_id>` | Просмотр списка или изменение и удаление автомобиля |
| `GET/POST` | `/api/masters` | Список мастеров и добавление мастера |
| `DELETE` | `/api/masters/<master_id>` | Удаление мастера |
| `GET/POST` | `/api/services` | Список услуг и добавление услуги |
| `PATCH/DELETE` | `/api/services/<service_id>` | Изменение или удаление услуги |
| `GET/POST` | `/api/warehouse/parts` | Список запчастей и добавление позиции |
| `PATCH` | `/api/warehouse/parts/<part_id>` | Изменение запчасти |
| `POST` | `/api/warehouse/incoming` | Поступление запчастей |
| `POST` | `/api/warehouse/writeoff` | Списание запчастей |
| `POST` | `/api/orders` | Создание заказа |
| `POST` | `/api/orders/<order_id>/items` | Добавление услуг и запчастей в заказ |
| `PATCH` | `/api/orders/<order_id>/status` | Изменение статуса заказа |
| `PATCH` | `/api/orders/<order_id>/master` | Назначение мастера |
| `GET` | `/api/orders/<order_id>/receipt` | Получение данных чека |

Пример создания заказа:

```bash
curl -X POST http://127.0.0.1:5000/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "car_id": 1,
    "master_id": 1,
    "status": "в работе",
    "services": [
      {"service_id": 1, "quantity": 1}
    ],
    "parts": [
      {"part_id": 1, "quantity": 2}
    ]
  }'
```
