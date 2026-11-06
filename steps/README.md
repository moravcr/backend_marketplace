# Снимки проекта по шагам пары 2

Каждая папка запускается отдельно. Зависимости общие (`pip install -r requirements.txt`, файл есть в каждой папке с приложением). Перед запуском скопируйте `.env.example` в `.env`.

| Папка | Что добавляется | Как запустить |
|---|---|---|
| `step1_sql_basics` | SQL руками: таблицы, запросы, JOIN, GROUP BY, ограничения, транзакция | `python sql_basics.py` |
| `step2_sql_injection` | SQL-инъекции: уязвимый и безопасный запрос, «вредная» строка как данные | `python injection_demo.py` |
| `step3_sqlalchemy` | SQLAlchemy: модели `Product` и `Order` (связь 1→N), CRUD товаров в базе, поиск `?q=`, `.env` | `uvicorn main:app --reload` |
| `step4_layers` | Слои: тонкие эндпоинты, `repository.py`, доменные ошибки | `uvicorn main:app --reload` |
| `step5_nested_orders` | Вложенный маршрут `/api/products/{id}/orders`, правило «не больше остатка» (409), транзакция; демо `transaction_demo.py` | `uvicorn main:app --reload`, демо: `python transaction_demo.py` |
| `step6_stats` | Статистика `GET /api/products/stats` (`GROUP BY`, `COUNT`, `SUM`, `AVG`), `seed.py --bulk`, `explain.py` | `uvicorn main:app --reload` |
| `step7_alembic` | Alembic: схему создаёт `alembic upgrade head`, `create_all` убран; демо `explain_demo.py` | `alembic upgrade head`, затем `uvicorn main:app --reload` |
| `step8_index_migration` | Миграция `0002`: индекс `ix_orders_product_id` (равно итоговому проекту) | `alembic upgrade head`, затем `uvicorn main:app --reload` |

Важно:

- Шаги 3–6 создают таблицы сами (`create_all`). Если вы меняете модели, **удалите `shop.db`**, иначе в старой базе не будет новых полей и индексов. Именно эту проблему решают миграции на шагах 7–8.
- Файл базы `shop.db` создаётся в той папке, откуда вы запускаете сервер. Каждый шаг имеет свою базу.
- Тестовые данные: `python seed.py` в папке шага. Для демонстрации индекса: `python seed.py --bulk 20000`, затем `python explain.py` (на шагах 6–8).
