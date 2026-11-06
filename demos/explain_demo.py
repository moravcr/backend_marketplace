"""Шаг 6–7. Индексы: сравниваем план и время запроса без индекса и с индексом.

Запуск (только Python):  python explain_demo.py
Схема такая же, как у таблицы orders в проекте.
"""
import random
import sqlite3
import time

PRODUCTS = 1_000
ORDERS = 300_000

conn = sqlite3.connect(":memory:")
conn.execute(
    """CREATE TABLE orders (
           id INTEGER PRIMARY KEY,
           product_id INTEGER NOT NULL,
           customer TEXT NOT NULL,
           quantity INTEGER NOT NULL,
           total REAL NOT NULL)"""
)
conn.executemany(
    "INSERT INTO orders (product_id, customer, quantity, total) VALUES (?, ?, ?, ?)",
    (
        (random.randint(1, PRODUCTS), f"Customer {i % 500}", random.randint(1, 5), random.random() * 1000)
        for i in range(ORDERS)
    ),
)
conn.commit()
print("В таблице orders " + f"{ORDERS:,}".replace(",", " ") + " строк, товаров " + f"{PRODUCTS:,}".replace(",", " ") + ".\n")

QUERY = "SELECT id, customer, quantity, total FROM orders WHERE product_id = ?"
TARGET = 777


def show_plan():
    for row in conn.execute("EXPLAIN QUERY PLAN " + QUERY, (TARGET,)):
        print("   план запроса:", row[-1])


def measure(repeats=50):
    start = time.perf_counter()
    for _ in range(repeats):
        conn.execute(QUERY, (TARGET,)).fetchall()
    return (time.perf_counter() - start) / repeats * 1000  # мс на один запрос


print("Запрос, который часто выполняет API (GET /api/products/{id}/orders):\n   ", QUERY)
print("\nДО индекса")
show_plan()
before = measure()
print(f"   среднее время одного запроса: {before:.3f} мс")

print("\nСоздаём индекс: CREATE INDEX ix_orders_product_id ON orders (product_id)")
conn.execute("CREATE INDEX ix_orders_product_id ON orders (product_id)")

print("\nПОСЛЕ индекса")
show_plan()
after = measure()
print(f"   среднее время одного запроса: {after:.3f} мс")

print(f"\nУскорение: примерно в {before / max(after, 1e-6):.0f} раз.")
print(
    "SCAN = база читает всю таблицу строка за строкой, SEARCH ... USING INDEX = быстро находит нужные строки по индексу.\n"
    "Цена индекса: он занимает место и немного замедляет INSERT/UPDATE. Поэтому индексы ставят на поля,\n"
    "по которым часто ищут, фильтруют и соединяют таблицы (внешние ключи — первые кандидаты)."
)
