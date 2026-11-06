"""Шаг 5. Транзакция: «проверить остаток, списать и записать заказ» — всё или ничего.

Запуск (только Python):  python transaction_demo.py
"""
import sqlite3

conn = sqlite3.connect(":memory:")
conn.executescript(
    """
    CREATE TABLE products (id INTEGER PRIMARY KEY, sku TEXT, stock INTEGER NOT NULL CHECK (stock >= 0));
    CREATE TABLE orders (id INTEGER PRIMARY KEY, product_id INTEGER, customer TEXT, quantity INTEGER);
    INSERT INTO products (id, sku, stock) VALUES (1, 'MOUSE-001', 3);
    """
)
conn.commit()


def state(label):
    stock = conn.execute("SELECT stock FROM products WHERE id = 1").fetchone()[0]
    orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    print(f"   [{label}] остаток = {stock}, заказов = {orders}")


def order_without_transaction(qty, crash):
    """ПЛОХО: каждый шаг фиксируется отдельно."""
    conn.execute("UPDATE products SET stock = stock - ? WHERE id = 1", (qty,))
    conn.commit()  # остаток уже списан и зафиксирован...
    if crash:
        raise RuntimeError("сервер упал до записи заказа")
    conn.execute("INSERT INTO orders (product_id, customer, quantity) VALUES (1, 'Ivanov', ?)", (qty,))
    conn.commit()


def order_in_transaction(qty, crash):
    """ХОРОШО: списание и запись заказа — одна транзакция."""
    try:
        cur = conn.execute("UPDATE products SET stock = stock - ? WHERE id = 1 AND stock >= ?", (qty, qty))
        if cur.rowcount == 0:
            raise ValueError("недостаточно товара на складе")
        if crash:
            raise RuntimeError("сервер упал до записи заказа")
        conn.execute("INSERT INTO orders (product_id, customer, quantity) VALUES (1, 'Ivanov', ?)", (qty,))
        conn.commit()  # фиксируем ВСЁ разом
    except Exception:
        conn.rollback()  # любая ошибка: отменяем ВСЕ изменения
        raise


def attempt(title, func, *args):
    print(f"\n=== {title}")
    state("до")
    try:
        func(*args)
        print("   результат: заказ оформлен")
    except Exception as e:
        print(f"   ОШИБКА: {e}")
    state("после")


attempt("1. Без транзакции, сбой посередине", order_without_transaction, 1, True)
print("   >>> Остаток уменьшился, а заказа нет: товар «потерян». Это нарушение атомарности.")

conn.execute("UPDATE products SET stock = 3")  # возвращаем исходное состояние
conn.commit()

attempt("2. В транзакции, сбой посередине", order_in_transaction, 1, True)
print("   >>> Откат вернул остаток: база выглядит так, будто попытки не было.")

attempt("3. В транзакции, без сбоя", order_in_transaction, 1, False)
attempt("4. В транзакции, заказываем больше, чем есть (осталось 2, нужно 5)", order_in_transaction, 5, False)
print("   >>> Условный UPDATE (WHERE stock >= ?) не даст уйти в минус, даже если два покупателя придут одновременно:")
print("       проверка и списание выполняются базой одной командой.")
