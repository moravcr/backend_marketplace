"""Шаг 2. SQL-инъекции: как ломают сырые запросы и как от этого защищаться.

Запуск (только Python, ничего устанавливать не нужно):  python injection_demo.py
"""
import sqlite3

conn = sqlite3.connect(":memory:")
conn.executescript(
    """
    CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL);
    INSERT INTO products (name, price) VALUES ('Wireless mouse', 1299.9), ('Mouse pad', 399.0);

    -- Таблица, которая НЕ должна быть доступна через поиск товаров
    CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT, password_hash TEXT);
    INSERT INTO users (email, password_hash) VALUES
        ('admin@shop.test', 'secret-hash-of-admin'),
        ('anna@shop.test',  'secret-hash-of-anna');
    """
)


def find_unsafe(name: str):
    """УЯЗВИМО: значение от пользователя склеивается со строкой запроса."""
    sql = f"SELECT id, name, price FROM products WHERE name = '{name}'"
    print("   SQL, который уйдёт в базу:\n   ", sql)
    return conn.execute(sql).fetchall()


def find_safe(name: str):
    """БЕЗОПАСНО: значение передаётся отдельно как параметр (?), оно никогда не станет частью SQL."""
    sql = "SELECT id, name, price FROM products WHERE name = ?"
    print("   SQL, который уйдёт в базу:\n   ", sql, "  + параметр:", repr(name))
    return conn.execute(sql, (name,)).fetchall()


def show(title, func, value):
    print(f"\n=== {title}\n   Ввод пользователя: {value!r}")
    try:
        for row in func(value):
            print("   ->", row)
    except Exception as e:
        print("   Ошибка:", type(e).__name__, "-", e)


show("1. Честный запрос (небезопасная функция)", find_unsafe, "Mouse pad")

show("2. Атака: условие «всегда истина» -> вернулись ВСЕ товары", find_unsafe, "x' OR '1'='1")

show(
    "3. Атака UNION: через поиск товаров вытащили таблицу пользователей",
    find_unsafe,
    "x' UNION SELECT id, email, password_hash FROM users --",
)

show("4. Атака «несколько команд» (в некоторых драйверах БД это сработало бы)", find_unsafe, "x'; DROP TABLE products; --")
print("   Таблица products на месте?", conn.execute("SELECT COUNT(*) FROM products").fetchone()[0], "строк")
print("   (sqlite3 запрещает несколько команд за раз, но PostgreSQL-драйверы и некоторые другие не всегда)")

print("\n##### Те же атаки против безопасной функции #####")
show("5. Условие «всегда истина»", find_safe, "x' OR '1'='1")
show("6. UNION", find_safe, "x' UNION SELECT id, email, password_hash FROM users --")
show("7. Честный запрос", find_safe, "Mouse pad")

print("\n##### Строка с «вредным» SQL как обычные ДАННЫЕ (пункт чек-листа лабы 2) #####")
EVIL = "'); DROP TABLE products;--"
conn.execute("INSERT INTO products (name, price) VALUES (?, ?)", (EVIL, 1.0))  # значение передано параметром
saved = conn.execute("SELECT name FROM products WHERE name = ?", (EVIL,)).fetchone()[0]
print("   Сохранили и прочитали обратно:", repr(saved))
print("   Строка сохранилась как обычный текст:", saved == EVIL)
print("   Таблица products на месте?", conn.execute("SELECT COUNT(*) FROM products").fetchone()[0], "строк")

print(
    """
Вывод: параметры запроса (?, :name, %s) решают проблему. Это то, что делает ORM под капотом:
    db.scalars(select(Product).where(Product.name == name))   # SQLAlchemy сам передаёт name параметром
Ни в одном запросе не склеивайте SQL из строк пользовательского ввода (f-строки, +, %, .format).
"""
)
