"""Слой доступа к данным: весь код, который общается с базой, живёт здесь.

Функции получают Session и данные, возвращают ORM-объекты и бросают доменные ошибки (не HTTP-ответы).
Благодаря этому эндпоинты в main.py остаются тонкими, а логику можно тестировать отдельно от веба.
"""
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from exceptions import ConflictError, NotFoundError
from models import Order, Product
from schemas import OrderCreate, ProductCreate, ProductPatch


# ---------- товары ----------

def get_product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError("Товар не найден")
    return product


def _commit_product(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Товар с таким sku уже существует")


def list_products(
    db: Session,
    *,
    limit: int,
    offset: int,
    q: str | None,
    sku: str | None,
    max_price: float | None,
) -> tuple[list[Product], int]:
    stmt = select(Product)
    if q:
        stmt = stmt.where(Product.name.icontains(q, autoescape=True))  # поиск выполняет БД
    if sku:
        stmt = stmt.where(Product.sku == sku)
    if max_price is not None:
        stmt = stmt.where(Product.price <= max_price)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(Product.id).limit(limit).offset(offset)).all()
    return list(items), total


def create_product(db: Session, data: ProductCreate) -> Product:
    product = Product(**data.model_dump())
    db.add(product)
    _commit_product(db)
    return product


def replace_product(db: Session, product_id: int, data: ProductCreate) -> Product:
    product = get_product(db, product_id)
    for key, value in data.model_dump().items():
        setattr(product, key, value)
    _commit_product(db)
    return product


def patch_product(db: Session, product_id: int, data: ProductPatch) -> Product:
    product = get_product(db, product_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    _commit_product(db)
    return product


def delete_product(db: Session, product_id: int) -> None:
    product = get_product(db, product_id)
    db.delete(product)
    try:
        db.commit()
    except IntegrityError:
        # Внешний ключ защищает целостность: нельзя удалить товар, на который есть заказы.
        db.rollback()
        raise ConflictError("Товар нельзя удалить: на него есть заказы")


# ---------- заказы товара (вложенный ресурс) ----------

def create_order(db: Session, product_id: int, data: OrderCreate) -> Order:
    """Создаёт заказ и списывает остаток ОДНОЙ транзакцией.

    Правило: нельзя заказать больше, чем есть на складе (иначе 409).
    Проверка и списание выполняются одной командой UPDATE ... WHERE stock >= :quantity:
    база атомарно проверяет условие и меняет остаток, поэтому даже два одновременных покупателя
    не уведут остаток в минус. Если после списания что-то пойдёт не так, rollback вернёт остаток.
    """
    product = get_product(db, product_id)  # 404, если товара нет
    try:
        reserved = db.execute(
            update(Product)
            .where(Product.id == product_id, Product.stock >= data.quantity)
            .values(stock=Product.stock - data.quantity)
            .execution_options(synchronize_session=False)
        )
        if reserved.rowcount == 0:  # условие не выполнилось: товара не хватает
            raise ConflictError(
                f"Недостаточно товара {product.sku}: на складе {product.stock}, в заказе {data.quantity}"
            )
        order = Order(
            product_id=product_id,
            customer=data.customer,
            quantity=data.quantity,
            unit_price=product.price,
            total=round(product.price * data.quantity, 2),
        )
        db.add(order)
        db.commit()  # единственная точка, где списание и заказ фиксируются вместе
    except Exception:
        db.rollback()  # любая ошибка: отменяем ВСЕ изменения этой транзакции
        raise
    return order


def list_orders(db: Session, product_id: int, *, limit: int, offset: int) -> tuple[list[Order], int]:
    get_product(db, product_id)  # 404, если товара нет
    stmt = select(Order).where(Order.product_id == product_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(Order.id).limit(limit).offset(offset)).all()
    return list(items), total


# ---------- статистика: все числа считает база (GROUP BY, COUNT, SUM, AVG) ----------

def get_stats(db: Session) -> dict:
    products_count, stock_total, avg_price = db.execute(
        select(
            func.count(Product.id),
            func.coalesce(func.sum(Product.stock), 0),
            func.coalesce(func.avg(Product.price), 0.0),
        )
    ).one()

    orders_count, units_sold, revenue = db.execute(
        select(
            func.count(Order.id),
            func.coalesce(func.sum(Order.quantity), 0),
            func.coalesce(func.sum(Order.total), 0.0),
        )
    ).one()

    # Статистика по каждому товару. LEFT JOIN, чтобы в результате были и товары без заказов.
    by_product = db.execute(
        select(
            Product.id,
            Product.name,
            func.count(Order.id).label("orders_count"),
            func.coalesce(func.sum(Order.quantity), 0).label("units_sold"),
            func.coalesce(func.sum(Order.total), 0.0).label("revenue"),
            func.coalesce(func.avg(Order.quantity), 0.0).label("avg_order_quantity"),
        )
        .select_from(Product)
        .outerjoin(Order, Order.product_id == Product.id)
        .group_by(Product.id, Product.name)
        .order_by(Product.id)
    ).all()

    return {
        "totals": {
            "products_count": products_count,
            "stock_total": int(stock_total),
            "avg_price": float(avg_price),
            "orders_count": orders_count,
            "units_sold": int(units_sold),
            "revenue": float(revenue),
        },
        "by_product": [
            {
                "product_id": row.id,
                "name": row.name,
                "orders_count": row.orders_count,
                "units_sold": int(row.units_sold),
                "revenue": float(row.revenue),
                "avg_order_quantity": float(row.avg_order_quantity),
            }
            for row in by_product
        ],
    }
