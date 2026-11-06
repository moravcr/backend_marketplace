"""Мини-маркетплейс API. Пара 2, шаг 4: тонкие эндпоинты, логика работы с БД в repository.py.

Запуск: uvicorn main:app --reload
Таблицы создаются при старте (create_all). Файл базы: shop.db.
Если поменяли модели, удалите shop.db: create_all не умеет менять уже существующие таблицы.
"""
import logging
import time

from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

import repository
from database import Base, engine, get_db
from exceptions import AppError
from schemas import ProductCreate, ProductOut, ProductPatch

Base.metadata.create_all(bind=engine)  # создать таблицы, которых ещё нет

app = FastAPI(
    title="Мини-маркетплейс API",
    description="Учебный REST API. Данные хранятся в базе данных.",
    version="2.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- товары ----------

@app.post("/api/products", response_model=ProductOut, status_code=201)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    return repository.create_product(db, data)


@app.get("/api/products", response_model=list[ProductOut])
def list_products(
    response: Response,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=100),
    sku: str | None = None,
    max_price: float | None = Query(None, gt=0),
    db: Session = Depends(get_db),
):
    items, total = repository.list_products(db, limit=limit, offset=offset, q=q, sku=sku, max_price=max_price)
    response.headers["X-Total-Count"] = str(total)
    return items


@app.get("/api/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    return repository.get_product(db, product_id)


@app.put("/api/products/{product_id}", response_model=ProductOut)
def replace_product(product_id: int, data: ProductCreate, db: Session = Depends(get_db)):
    return repository.replace_product(db, product_id, data)


@app.patch("/api/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductPatch, db: Session = Depends(get_db)):
    return repository.patch_product(db, product_id, data)


@app.delete("/api/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    repository.delete_product(db, product_id)
    return Response(status_code=204)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    """Ошибки фреймворка (неизвестный адрес, неверный метод) -> {"error": "..."}"""
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """Наши доменные ошибки: 400 / 404 / 409."""
    content = {"error": exc.message}
    if exc.status_code == 400:
        content["field"] = exc.field
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Ошибки валидации Pydantic -> 400 и {"error": "...", "field": "..."}"""
    first = exc.errors()[0]
    if first["type"] == "json_invalid":
        return JSONResponse(status_code=400, content={"error": "Некорректный JSON", "field": None})
    parts = [str(p) for p in first["loc"][1:]]  # loc = ("body", "customer") -> "customer"
    field = ".".join(parts) if parts else None
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
