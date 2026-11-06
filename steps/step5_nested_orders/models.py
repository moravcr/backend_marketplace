"""ORM-модели: Python-классы, которые SQLAlchemy превращает в таблицы."""
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        # Последний рубеж обороны: даже если в код проскочит ошибка, база не пропустит плохие данные
        CheckConstraint("price > 0", name="ck_products_price_positive"),
        CheckConstraint("stock >= 0", name="ck_products_stock_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[float] = mapped_column(Float)  # в настоящем магазине для денег берут Numeric/Decimal или копейки в int
    sku: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # unique + index: быстрый поиск и защита от дублей
    stock: Mapped[int] = mapped_column(Integer, default=0)

    # Связь «один ко многим»: у товара много заказов.
    # passive_deletes="all": ORM не трогает заказы при удалении товара, решение за внешним ключом базы (он запретит).
    orders: Mapped[list["Order"]] = relationship(back_populates="product", passive_deletes="all")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_orders_quantity_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    customer: Mapped[str] = mapped_column(String(100))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)  # цена на момент заказа: потом цена товара может измениться
    total: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    product: Mapped["Product"] = relationship(back_populates="orders")
