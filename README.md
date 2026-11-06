# Мини-маркетплейс API, часть 2: база данных

Продолжение проекта с пары 1. Те же эндпоинты товаров, но данные теперь лежат **в реляционной базе** (SQLite или PostgreSQL) и переживают перезапуск. Появилась вторая сущность **Заказ** (один товар — много заказов) с **вложенным маршрутом** `/api/products/{id}/orders`, транзакцией, поиском, статистикой, индексом и миграциями.

## Быстрый старт

Нужен Python 3.10+.

```bash
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# macOS / Linux:         source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
alembic upgrade head          # создать схему базы из миграций
python seed.py                # заполнить пустую базу тестовыми данными
uvicorn main:app --reload
```

- Сервис: http://127.0.0.1:8000 · Swagger: http://127.0.0.1:8000/docs
- Примеры запросов: `requests.http`
- Файл базы SQLite: `shop.db` (создаётся рядом с проектом). **Чтобы начать заново:** остановите сервер, удалите `shop.db`, выполните `alembic upgrade head` и `python seed.py`.

## Соответствие чек-листу лабораторной 2

| Пункт лабораторной | Где в проекте | Как проверить |
|---|---|---|
| Запись переживает перезапуск | данные в `shop.db` (или PostgreSQL) | создать товар (POST), перезапустить `uvicorn`, получить его (GET) |
| Вторая сущность с внешним ключом, вложенный маршрут: создание и список | модель `Order` (`product_id` → `products.id`), `POST` и `GET /api/products/{id}/orders` | запросы из раздела «Заказы товара» в `requests.http` |
| Схема создаётся из репозитория | миграции Alembic в `migrations/` | `alembic upgrade head` на пустой базе |
| Строка подключения из окружения, `.env.example`, пароля в коде нет | `database.py` читает `DATABASE_URL`, шаблон — `.env.example`, `.env` в `.gitignore` | открыть `database.py` и `.env.example` |
| ER-диаграмма в README | раздел «ER-диаграмма» ниже | — |
| Строка `'); DROP TABLE <table>;--` сохраняется как текст | все значения передаются параметрами через ORM | запрос «DROP TABLE как данные» в `requests.http`, демо `demos/injection_demo.py` |
| ★ Миграции и сиды | `migrations/`, `python seed.py` | `alembic upgrade head`, затем `python seed.py` |
| ★ Индекс миграцией, EXPLAIN в README | миграция `0002`, раздел «Индекс и EXPLAIN» ниже, `explain.py` | `alembic upgrade 0001` → `python explain.py` → `alembic upgrade head` → `python explain.py` |
| ★ Поиск `?q=` без учёта регистра, ищет база | `GET /api/products?q=mouse` | `q=mouse`, `q=MOUSE`, для кириллицы тоже работает |
| ★★ Правило темы, 409, проверка и запись в одной транзакции | нельзя заказать больше, чем есть на складе | запросы из раздела «Правило (409)» в `requests.http` |
| ★★ Статистика на `GROUP BY`, `COUNT`, `SUM`, `AVG` | `GET /api/products/stats` | запрос в `requests.http` |

Для чекера `backcheck` подготовлен фрагмент **`contract.lab2.json`**: это то, что нужно **добавить** в существующий `contract.json` (см. раздел в конце).

## ER-диаграмма

```mermaid
erDiagram
    PRODUCTS ||--o{ ORDERS : "has"
    PRODUCTS {
        int id PK
        string name
        float price
        string sku UK
        int stock
    }
    ORDERS {
        int id PK
        int product_id FK
        string customer
        int quantity
        float unit_price
        float total
        datetime created_at
    }
```

Один товар — много заказов. Ограничения на уровне базы: `price > 0`, `stock >= 0`, `quantity > 0`, `sku` уникален, `orders.product_id` ссылается на существующий товар (товар с заказами удалить нельзя).

## Структура проекта

```
main.py            HTTP-слой: эндпоинты, обработчики ошибок, лог запросов
repository.py      слой данных: все запросы к БД, транзакция заказа, статистика
models.py          ORM-модели (таблицы): Product, Order
schemas.py         Pydantic-схемы (формат запросов и ответов API)
database.py        подключение: engine, сессии, DATABASE_URL из окружения
exceptions.py      доменные ошибки (400, 404, 409)
seed.py            сиды: тестовые данные, `--bulk N` для больших объёмов
explain.py         печатает план выполнения запроса (EXPLAIN)
alembic.ini        настройки Alembic
migrations/        миграции схемы БД (versions/0001..., 0002...)
.env.example       шаблон переменных окружения (без секретов)
requests.http      все запросы
contract.lab2.json что добавить в contract.json для чекера
demos/             учебные скрипты на чистом Python (ничего ставить не нужно)
steps/             снимки проекта после каждого шага пары
```

## Эндпоинты

| Метод | Путь | Что делает | Успех | Ошибки |
|---|---|---|---|---|
| GET | `/health` | проверка работы | 200 | — |
| POST | `/api/products` | создать товар | 201 | 400, 409 (дубликат sku) |
| GET | `/api/products` | список: `q`, `sku`, `max_price`, `limit`, `offset` | 200 | 400 |
| GET | `/api/products/stats` | статистика (агрегаты в БД) | 200 | — |
| GET | `/api/products/{id}` | один товар | 200 | 404 |
| PUT | `/api/products/{id}` | заменить целиком | 200 | 400, 404, 409 |
| PATCH | `/api/products/{id}` | изменить часть полей | 200 | 400, 404, 409 |
| DELETE | `/api/products/{id}` | удалить | 204 | 404, 409 (есть заказы) |
| POST | `/api/products/{id}/orders` | создать заказ товара | 201 | 400, 404, 409 (не хватает на складе) |
| GET | `/api/products/{id}/orders` | список заказов товара | 200 | 400, 404 |

Списки отдают общее число записей в заголовке `X-Total-Count`.

Тело `POST /api/products/{id}/orders`:

```json
{"customer": "Ivanov", "quantity": 2}
```

Ответ содержит `id`, `product_id`, `customer`, `quantity`, `unit_price`, `total`, `created_at`.

## Формат ошибок

```json
{"error": "Field required", "field": "customer"}
```

- `400` — ошибка валидации (сломанный JSON тоже: тогда `field` равно `null`).
- `404` и `409` — `{"error": "текст"}`.

## Правило темы: нельзя заказать больше, чем на складе

`POST /api/products/{id}/orders` выполняет **в одной транзакции**: проверку остатка, списание и запись заказа. Проверка и списание сделаны одной командой:

```sql
UPDATE products SET stock = stock - :quantity WHERE id = :id AND stock >= :quantity
```

Если команда не затронула ни одной строки, значит товара не хватает: транзакция откатывается и сервер отвечает **409** с объяснением (`Недостаточно товара KEYB-001: на складе 0, в заказе 1`). Благодаря условию в `WHERE` остаток не уйдёт в минус, даже если два покупателя оформят заказ одновременно. Если после списания возникнет любая ошибка, `rollback` вернёт остаток (наглядно: `python demos/transaction_demo.py`).

## Статистика

`GET /api/products/stats` возвращает `totals` (всего товаров, остатки, средняя цена, число заказов, проданные штуки, выручка) и `by_product` (заказы, штуки, выручка и средний размер заказа по каждому товару). Все числа считает база запросами с `COUNT`, `SUM`, `AVG` и `GROUP BY` (см. `get_stats` в `repository.py`); цикла по данным в Python нет.

Маршрут `/api/products/stats` объявлен **выше** `/api/products/{product_id}`, иначе слово `stats` было бы принято за id товара.

## Индекс и EXPLAIN

Частый запрос API: заказы одного товара (`GET /api/products/{id}/orders`, а также `JOIN` в статистике):

```sql
SELECT id, customer, quantity, total FROM orders WHERE product_id = 777
```

Индекс `ix_orders_product_id` создаёт миграция `0002` (`migrations/versions/0002_add_orders_product_id_index.py`). Как воспроизвести:

```bash
alembic upgrade 0001          # схема без индекса
python seed.py --bulk 20000   # много данных: на малых таблицах разницы не видно
python explain.py             # план БЕЗ индекса
alembic upgrade head          # применяем миграцию 0002 (создаёт индекс)
python explain.py             # план С индексом
```

Пример вывода для SQLite (таблица на 100 000 заказов; у вас номера и порядок строк могут отличаться):

```text
до миграции:    SCAN orders
после миграции: SEARCH orders USING INDEX ix_orders_product_id (product_id=?)
```

`SCAN` означает полное чтение таблицы, `SEARCH ... USING INDEX` означает, что база использует индекс. Для PostgreSQL `explain.py` выполняет `EXPLAIN` (ищите `Index Scan` / `Bitmap Index Scan` вместо `Seq Scan`). Для самостоятельного сравнения времени без проекта: `python demos/explain_demo.py`.

## Миграции Alembic: шпаргалка

```bash
alembic upgrade head                                   # применить все миграции
alembic upgrade 0001                                   # применить только до версии 0001
alembic current                                        # какая версия сейчас в базе
alembic history                                        # список миграций
alembic revision --autogenerate -m "add something"     # создать миграцию по изменениям в models.py
alembic downgrade -1                                   # откатить последнюю миграцию
```

Типичный сценарий: меняем `models.py`, выполняем `alembic revision --autogenerate -m "..."`, **читаем созданный файл** в `migrations/versions/`, затем `alembic upgrade head`.

## PostgreSQL вместо SQLite (по желанию)

Код не привязан к SQLite. Чтобы работать с PostgreSQL:

1. Установите драйвер: `pip install "psycopg[binary]"`.
2. Создайте базу (например, `shop`) и пользователя.
3. В `.env` укажите строку подключения (шаблон есть в `.env.example`), например `DATABASE_URL=postgresql+psycopg://shop_user:ВАШ_ПАРОЛЬ@localhost:5432/shop`.
4. Выполните `alembic upgrade head` и `python seed.py`.

Пароль хранится только в `.env`, который не попадает в git.

## contract.json для чекера

Файл `contract.lab2.json` содержит блок полей для лабораторной 2 (`text_field`, `search`, `child`, `rule`, `stats_path`). Добавьте его **в существующий** `contract.json`, а не вместо него. Поля соответствуют этому проекту: `text_field` — `name` товара, ребёнок — `orders`, связь — `product_id`, правило — нельзя заказать больше остатка (`parent: {"stock": 1}`, второй заказ даёт 409), статистика — `/api/products/stats`.

## Работа со снимками `steps/`

Каждая папка в `steps/` содержит рабочий проект на конкретном шаге пары. Если вы отстали, откройте нужную папку (подробности в `steps/README.md`).

## Частые проблемы

| Симптом | Причина и решение |
|---|---|
| `no such table: products` | Не применены миграции: `alembic upgrade head` |
| Список пуст после запуска | База пустая: `python seed.py` или создайте данные через POST |
| `table products already exists` при `alembic upgrade head` | База создана не миграциями (`create_all` из снимков 3–6): удалите `shop.db` и повторите |
| `Target database is not up to date` при `alembic revision --autogenerate` | Сначала `alembic upgrade head` |
| `GET /api/products/stats` возвращает 400 | Маршрут `stats` объявлен ниже `/{product_id}`: перенесите выше |
| `python explain.py` пишет, что заказов нет | Выполните `python seed.py --bulk 20000` |
| Хочу всё сбросить | Остановите сервер, удалите `shop.db`, `alembic upgrade head`, `python seed.py` |
