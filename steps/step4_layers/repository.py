"""Слой доступа к данным: весь код, который общается с базой, живёт здесь.

Функции получают Session и данные, возвращают ORM-объекты и бросают доменные ошибки (не HTTP-ответы).
Благодаря этому эндпоинты в main.py остаются тонкими, а логику можно тестировать отдельно от веба.
"""
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from exceptions import ConflictError, NotFoundError
from models import Product
from schemas import ProductCreate, ProductPatch


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
