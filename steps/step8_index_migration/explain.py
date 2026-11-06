"""Показывает, как база выполняет запрос «заказы товара»: python explain.py

Порядок для README (см. раздел про индекс):
    alembic upgrade 0001            # схема без индекса
    python seed.py --bulk 20000     # много данных, иначе разницы не видно
    python explain.py               # план БЕЗ индекса: SCAN
    alembic upgrade head            # миграция 0002 создаёт индекс
    python explain.py               # план С индексом: SEARCH ... USING INDEX
"""
from sqlalchemy import text

from database import IS_SQLITE, engine

QUERY = "SELECT id, customer, quantity, total FROM orders WHERE product_id = {pid}"


def main():
    with engine.connect() as conn:
        pid = conn.execute(text("SELECT product_id FROM orders LIMIT 1")).scalar()
        if pid is None:
            print("В таблице orders нет данных. Выполните: python seed.py --bulk 20000")
            return
        # pid — число, полученное из БД; int() гарантирует, что в запрос не попадёт посторонний текст.
        query = QUERY.format(pid=int(pid))
        prefix = "EXPLAIN QUERY PLAN " if IS_SQLITE else "EXPLAIN "
        print("Запрос:\n   ", query)
        print("План выполнения:")
        for row in conn.execute(text(prefix + query)).fetchall():
            print("   ", row[-1] if IS_SQLITE else row[0])


if __name__ == "__main__":
    main()
