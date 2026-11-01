"""Мини-маркетплейс: API товаров (практика, пара 1) — финальная версия."""

import itertools
import logging
import time

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException


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
def list_products(
    response: Response,
    limit: int = Query(10, ge=1, le=100),  # сколько записей отдать
    offset: int = Query(0, ge=0),  # сколько пропустить с начала
    name: str | None = None,  # фильтр: подстрока в названии
    sku: str | None = None,  # фильтр: точное совпадение
    max_price: float | None = Query(None, gt=0),  # фильтр: цена не выше
):
    items = list(products.values())
    if name:
        items = [p for p in items if name.lower() in p.name.lower()]
    if sku:
        items = [p for p in items if p.sku == sku]
    if max_price is not None:
        items = [p for p in items if p.price <= max_price]

    response.headers["X-Total-Count"] = str(len(items))  # всего подходящих записей
    return items[offset : offset + limit]


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


@app.delete("/api/products/{product_id}", status_code=204)
def delete_product(product_id: int):
    get_or_404(product_id)
    del products[product_id]
    return Response(status_code=204)  # 204 No Content: тела ответа нет


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    """404, 405, 409... -> {"error": "..."}"""
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Любая ошибка валидации -> 400 и {"error": "...", "field": "..."}"""
    first = exc.errors()[0]
    if first["type"] == "json_invalid":
        return JSONResponse(
            status_code=400, content={"error": "Некорректный JSON", "field": None}
        )
    loc = first["loc"]  # например ("body", "price") или ("query", "limit")
    field = loc[-1] if len(loc) > 1 and isinstance(loc[-1], str) else None
    return JSONResponse(status_code=400, content={"error": first["msg"], "field": field})


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("api")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Строка лога на каждый запрос: GET /api/products/7 404 1.3ms"""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(f"{request.method} {request.url.path} {response.status_code} {elapsed_ms:.1f}ms")
    return response
