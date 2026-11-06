"""Pydantic-схемы: что принимает и что отдаёт API (это не то же самое, что ORM-модели)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    """Создание (POST) и полная замена (PUT)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0)
    sku: str = Field(min_length=1, max_length=50)
    stock: int = Field(default=0, ge=0)


class ProductPatch(BaseModel):
    """Частичное обновление (PATCH): все поля необязательные, но null присылать нельзя."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(default=None, min_length=1, max_length=100)
    price: float = Field(default=None, gt=0)
    sku: str = Field(default=None, min_length=1, max_length=50)
    stock: int = Field(default=None, ge=0)


class ProductOut(BaseModel):
    """Товар в ответе API. from_attributes позволяет собрать схему прямо из ORM-объекта."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: float
    sku: str
    stock: int


class OrderCreate(BaseModel):
    """Тело POST /api/products/{id}/orders. Товар берётся из адреса, поэтому product_id в теле не нужен."""

    model_config = ConfigDict(str_strip_whitespace=True)

    customer: str = Field(min_length=1, max_length=100)
    quantity: int = Field(ge=1, le=1000)


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    customer: str
    quantity: int
    unit_price: float
    total: float
    created_at: datetime
