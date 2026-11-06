"""Сиды: наполняют пустую базу тестовыми данными.

    python seed.py              тестовые товары и заказы (безопасно запускать повторно)
    python seed.py --bulk 20000 ещё 20000 сгенерированных товаров и по 5 заказов на каждый
                                (нужно, чтобы на EXPLAIN было видно разницу с индексом и без)
"""
import argparse
import random
from datetime import datetime, timezone

from sqlalchemy import func, insert, select

from database import Base, SessionLocal, engine
from models import Order, Product

CHUNK = 5000


def seed_sample(db):
    if db.scalars(select(Product).where(~Product.sku.like("BULK-%"))).first() is not None:
        print("Тестовые данные уже есть, пропускаем.")
        return
    mouse = Product(name="Wireless mouse", price=1299.90, sku="MOUSE-001", stock=22)
    gaming = Product(name="Gaming mouse", price=2990.00, sku="MOUSE-002", stock=12)
    keyboard = Product(name="Mechanical keyboard", price=5490.00, sku="KEYB-001", stock=9)
    pad = Product(name="Mouse pad", price=399.00, sku="PAD-001", stock=100)
    cable = Product(name="USB cable", price=199.00, sku="CABLE-001", stock=50)
    db.add_all([mouse, gaming, keyboard, pad, cable])
    db.flush()  # получаем id товаров
    db.add_all(
        [
            Order(product_id=mouse.id, customer="Ivanov", quantity=2, unit_price=mouse.price, total=round(mouse.price * 2, 2)),
            Order(product_id=mouse.id, customer="Petrov", quantity=1, unit_price=mouse.price, total=mouse.price),
            Order(product_id=keyboard.id, customer="Ivanov", quantity=1, unit_price=keyboard.price, total=keyboard.price),
        ]
    )
    db.commit()
    print("Готово: 5 товаров и 3 заказа.")


def seed_bulk(db, n):
    existing = db.scalar(select(func.count()).select_from(Product).where(Product.sku.like("BULK-%")))
    if existing >= n:
        print(f"Сгенерированных товаров уже {existing}, ничего не добавляем.")
        return
    first_new = existing + 1
    rows = [
        {
            "name": f"Bulk product {i}",
            "price": round(random.uniform(10, 5000), 2),
            "sku": f"BULK-{i:07d}",
            "stock": random.randint(0, 500),
        }
        for i in range(first_new, n + 1)
    ]
    for start in range(0, len(rows), CHUNK):
        db.execute(insert(Product), rows[start : start + CHUNK])
    db.commit()

    new_products = db.execute(
        select(Product.id, Product.price).where(Product.sku >= f"BULK-{first_new:07d}", Product.sku.like("BULK-%"))
    ).all()
    now = datetime.now(timezone.utc)
    orders = []
    for product_id, price in new_products:
        for _ in range(5):
            quantity = random.randint(1, 5)
            orders.append(
                {
                    "product_id": product_id,
                    "customer": f"Customer {random.randint(1, 1000)}",
                    "quantity": quantity,
                    "unit_price": price,
                    "total": round(price * quantity, 2),
                    "created_at": now,
                }
            )
    for start in range(0, len(orders), CHUNK):
        db.execute(insert(Order), orders[start : start + CHUNK])
    db.commit()
    print(f"Добавлено товаров: {len(rows)}, заказов: {len(orders)}.")


def main():
    parser = argparse.ArgumentParser(description="Наполнение базы тестовыми данными")
    parser.add_argument("--bulk", type=int, metavar="N", help="сгенерировать N товаров (и 5*N заказов)")
    args = parser.parse_args()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_sample(db)
        if args.bulk:
            seed_bulk(db, args.bulk)


if __name__ == "__main__":
    main()
