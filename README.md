# Домашнее задание 6: фоновые задачи и кеширование

Проект демонстрирует FastAPI-приложение с SQLAlchemy, фоновыми задачами `BackgroundTasks` и кешированием ответов через Redis.

## Возможности

- `POST /tasks/import-csv?csv_path=...` — запускает фоновое наполнение БД из CSV-файла.
- `POST /tasks/delete-products` — запускает фоновое удаление товаров по списку `ids`.
- `GET /products` и `GET /products/{product_id}` — возвращают данные пользователю и кешируют ответы в Redis.
- `POST /products` — создает товар и инвалидирует кеш списка/карточки товаров.

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Запустите Redis локально, например через Docker:

```bash
docker run --name hw6-redis -p 6379:6379 -d redis:7-alpine
```

Запустите приложение:

```bash
uvicorn app.main:app --reload
```

Откройте документацию API: <http://127.0.0.1:8000/docs>.

## Примеры запросов

Импорт тестового CSV-файла:

```bash
curl -X POST "http://127.0.0.1:8000/tasks/import-csv?csv_path=data/products.csv"
```

Получение списка товаров с кешированием в Redis:

```bash
curl "http://127.0.0.1:8000/products"
```

Удаление товаров в фоне:

```bash
curl -X POST "http://127.0.0.1:8000/tasks/delete-products" \
  -H "Content-Type: application/json" \
  -d '{"ids":[1,2]}'
```

## Переменные окружения

- `DATABASE_URL` — строка подключения SQLAlchemy, по умолчанию `sqlite:///./app.db`.
- `REDIS_URL` — строка подключения Redis, по умолчанию `redis://localhost:6379/0`.
- `CACHE_TTL_SECONDS` — TTL кеша в секундах, по умолчанию `60`.
- `CACHE_ENABLED` — включает или отключает кеширование, по умолчанию `true`.
