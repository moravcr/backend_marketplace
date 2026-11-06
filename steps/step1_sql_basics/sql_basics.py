"""Шаг 1. SQL руками: таблицы, запросы, JOIN, GROUP BY, ограничения, транзакция.

Запуск (ничего устанавливать не нужно, только Python):  python sql_basics.py
Работает с базой в памяти и каждый раз создаёт её заново из shop.sql.
"""
import sqlite3
from pathlib import Path

conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")  # в SQLite внешние ключи по умолчанию выключены!
conn.executescript(Path(__file__).with_name("shop.sql").read_text(encoding="utf-8"))


def run(title, sql, params=()):
    print(f"\n=== {title}")
    print(sql.strip())
    try:
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        for row in rows:
            print("   ", tuple(row))
        if cur.description is None:
            print("    OK, затронуто строк:", cur.rowcount)
    except sqlite3.Error as e:
        print("    ОШИБКА БАЗЫ ДАННЫХ:", type(e).__name__, "-", e)


run("1. Все товары", "SELECT * FROM products")

run("2. Фильтр и сортировка", "SELECT name, price FROM products WHERE price < 3000 ORDER BY price DESC")

run(
    "3. JOIN: заказы вместе с названием товара",
    """SELECT o.id, o.customer, p.name AS product, o.quantity
       FROM orders o
       JOIN products p ON p.id = o.product_id""",
)

run(
    "4. LEFT JOIN: товары без заказов тоже попадают в результат",
    """SELECT p.name, o.customer
       FROM products p
       LEFT JOIN orders o ON o.product_id = p.id""",
)

run(
    "5. GROUP BY: по каждому товару число заказов, штук, выручка и средний размер заказа",
    """SELECT p.name,
              COUNT(o.id)                    AS orders_count,
              COALESCE(SUM(o.quantity), 0)   AS units_sold,
              ROUND(COALESCE(SUM(o.total), 0), 2) AS revenue,
              COALESCE(AVG(o.quantity), 0)   AS avg_order_quantity
       FROM products p
       LEFT JOIN orders o ON o.product_id = p.id
       GROUP BY p.id""",
)

print("\n##### База сама защищает данные (ограничения схемы) #####")
run("6. Отрицательная цена (CHECK)", "INSERT INTO products (name, price, sku) VALUES ('Bad', -5, 'BAD-1')")
run("7. Повторный артикул (UNIQUE)", "INSERT INTO products (name, price, sku) VALUES ('Clone', 10, 'MOUSE-001')")
run("8. Заказ несуществующего товара (FOREIGN KEY)", "INSERT INTO orders (product_id, customer, quantity, unit_price, total) VALUES (999, 'Ghost', 1, 10, 10)")
run("9. Отрицательный остаток (CHECK)", "UPDATE products SET stock = -1 WHERE sku = 'MOUSE-001'")
run("10. Нельзя удалить товар, на который есть заказы (FOREIGN KEY)", "DELETE FROM products WHERE id = 1")

print("\n##### Транзакция: всё или ничего #####")
run("11. Остаток до", "SELECT sku, stock FROM products WHERE sku = 'MOUSE-001'")
run("12. Уменьшаем остаток на 5 (изменение пока не зафиксировано)", "UPDATE products SET stock = stock - 5 WHERE sku = 'MOUSE-001'")
run("13. Внутри транзакции остаток уже 17", "SELECT sku, stock FROM products WHERE sku = 'MOUSE-001'")
conn.rollback()
print("\n>>> ROLLBACK: отменяем незафиксированные изменения")
run("14. После отката остаток снова 22", "SELECT sku, stock FROM products WHERE sku = 'MOUSE-001'")
