"""Мини-маркетплейс API. Пара 2, шаг 3: товары хранятся в базе (SQLAlchemy + SQLite).

Запуск: uvicorn main:app --reload
Таблицы создаются при старте (create_all). Файл базы: shop.db. Если поменяли модели, удалите shop.db.
Здесь вся работа с БД прямо в эндпоинтах. На шаге 4 мы вынесем её в отдельный слой (repository.py).
"""
import logging
import time

from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from database import Base, engine, get_db
from exceptions import AppError, ConflictError, NotFoundError
from models import Product
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


# ---------- вспомогательные функции ----------

def get_or_404(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)  # SELECT ... WHERE id = :id
    if product is None:
        raise NotFoundError("Товар не найден")
    return product


def commit_or_conflict(db: Session) -> None:
    """Фиксируем изменения. Если нарушено ограничение UNIQUE, база выбросит IntegrityError."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Товар с таким sku уже существует")


# ---------- товары ----------

@app.post("/api/products", response_model=ProductOut, status_code=201)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    product = Product(**data.model_dump())
    db.add(product)  # поставили в очередь на INSERT
    commit_or_conflict(db)  # INSERT выполняется здесь, id выдаёт база
    return product


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
    stmt = select(Product)
    if q:
        # Поиск по названию без учёта регистра выполняет БД: WHERE lower(name) LIKE '%q%'.
        # autoescape: символы % и _ в запросе пользователя не работают как маски.
        stmt = stmt.where(Product.name.icontains(q, autoescape=True))
    if sku:
        stmt = stmt.where(Product.sku == sku)
    if max_price is not None:
        stmt = stmt.where(Product.price <= max_price)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total)
    return db.scalars(stmt.order_by(Product.id).limit(limit).offset(offset)).all()


@app.get("/api/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, product_id)


@app.put("/api/products/{product_id}", response_model=ProductOut)
def replace_product(product_id: int, data: ProductCreate, db: Session = Depends(get_db)):
    product = get_or_404(db, product_id)
    for key, value in data.model_dump().items():
        setattr(product, key, value)  # меняем объект, SQLAlchemy сам сформирует UPDATE
    commit_or_conflict(db)
    return product


@app.patch("/api/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductPatch, db: Session = Depends(get_db)):
    product = get_or_404(db, product_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    commit_or_conflict(db)
    return product


@app.delete("/api/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = get_or_404(db, product_id)
    db.delete(product)
    try:
        db.commit()
    except IntegrityError:
        # Внешний ключ защищает целостность: нельзя удалить товар, на который есть заказы.
        db.rollback()
        raise ConflictError("Товар нельзя удалить: на него есть заказы")
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
