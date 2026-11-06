-- Учебная схема магазина (SQLite). Запускается скриптом sql_basics.py
CREATE TABLE products (
    id    INTEGER PRIMARY KEY,
    name  TEXT    NOT NULL,
    price REAL    NOT NULL CHECK (price > 0),
    sku   TEXT    NOT NULL UNIQUE,
    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0)
);

CREATE TABLE orders (
    id         INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products (id),
    customer   TEXT    NOT NULL,
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL    NOT NULL,
    total      REAL    NOT NULL
);

INSERT INTO products (id, name, price, sku, stock) VALUES
    (1, 'Wireless mouse',      1299.90, 'MOUSE-001', 22),
    (2, 'Gaming mouse',        2990.00, 'MOUSE-002', 12),
    (3, 'Mechanical keyboard', 5490.00, 'KEYB-001',  10),
    (4, 'Mouse pad',            399.00, 'PAD-001',  100);

INSERT INTO orders (product_id, customer, quantity, unit_price, total) VALUES
    (1, 'Ivanov', 2, 1299.90, 2599.80),
    (1, 'Petrov', 1, 1299.90, 1299.90),
    (3, 'Ivanov', 1, 5490.00, 5490.00);
