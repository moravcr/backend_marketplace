"""Мини-маркетплейс: API товаров (практика, пара 1) — Шаг 4: PUT и PATCH."""

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


def get_or_404(product_id: int) -> Product:
    product = products.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product


@app.get("/api/products", response_model=list[Product])
def list_products():
    return list(products.values())


@app.get("/api/products/{product_id}", response_model=Product)
def get_product(product_id: int):
    return get_or_404(product_id)


class ProductPatch(BaseModel):
    """Частичное обновление (PATCH): можно прислать любое подмножество полей."""

    model_config = ConfigDict(str_strip_whitespace=True)

    # Тип str (не "str | None"): поле можно НЕ передавать, но нельзя передать null.
    name: str = Field(default=None, min_length=1, max_length=100)
    price: float = Field(default=None, gt=0)
    sku: str = Field(default=None, min_length=1, max_length=50)
    stock: int = Field(default=None, ge=0)


@app.put("/api/products/{product_id}", response_model=Product)
def replace_product(product_id: int, data: ProductCreate):
    """PUT: полная замена. Нужно прислать ВСЕ поля. Идемпотентен."""
    get_or_404(product_id)
    check_sku_unique(data.sku, exclude_id=product_id)
    product = Product(id=product_id, **data.model_dump())
    products[product_id] = product
    return product


@app.patch("/api/products/{product_id}", response_model=Product)
def update_product(product_id: int, data: ProductPatch):
    """PATCH: меняем только те поля, которые прислал клиент."""
    product = get_or_404(product_id)
    changes = data.model_dump(exclude_unset=True)
    if "sku" in changes:
        check_sku_unique(changes["sku"], exclude_id=product_id)
    updated = product.model_copy(update=changes)
    products[product_id] = updated
    return updated
