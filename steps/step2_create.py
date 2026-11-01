"""Мини-маркетплейс: API товаров (практика, пара 1) — Шаг 2: модели и POST."""

import itertools

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field


app = FastAPI(
    title="Мини-маркетплейс API",
    description="Учебный REST API товаров. Данные хранятся в памяти.",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


class ProductCreate(BaseModel):
    """Что присылает клиент при создании (POST) и полной замене (PUT)."""

    model_config = ConfigDict(str_strip_whitespace=True)  # "  abc " -> "abc", "   " -> ""

    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0)
    sku: str = Field(min_length=1, max_length=50)
    stock: int = Field(default=0, ge=0)


class Product(ProductCreate):
    """Товар, как мы отдаём его клиенту: те же поля + id."""

    id: int


# "База данных" в памяти: id -> товар
products: dict[int, Product] = {}
id_counter = itertools.count(1)


def check_sku_unique(sku: str, exclude_id: int | None = None) -> None:
    for p in products.values():
        if p.sku == sku and p.id != exclude_id:
            raise HTTPException(status_code=409, detail="Товар с таким sku уже существует")


@app.post("/api/products", response_model=Product, status_code=201)
def create_product(data: ProductCreate):
    check_sku_unique(data.sku)
    product = Product(id=next(id_counter), **data.model_dump())
    products[product.id] = product
    return product
