"""Подключение к базе данных: engine, сессии, базовый класс моделей."""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()  # читаем файл .env (если он есть) и кладём значения в переменные окружения

# Строка подключения берётся из переменной окружения DATABASE_URL (см. .env.example).
# Пароль в код не записываем: он живёт в .env, а .env не попадает в git.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shop.db")

IS_SQLITE = DATABASE_URL.startswith("sqlite")

# check_same_thread=False: FastAPI обрабатывает запросы в разных потоках, SQLite по умолчанию это запрещает.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if IS_SQLITE else {})


def _unicode_lower(value):
    return value.lower() if isinstance(value, str) else value


@event.listens_for(engine, "connect")
def configure_sqlite(dbapi_connection, connection_record):
    """Настройки только для SQLite."""
    if not IS_SQLITE:
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")  # внешние ключи в SQLite по умолчанию выключены
    cursor.close()
    # Встроенная lower() в SQLite понимает только латиницу. Подменяем её на версию из Python,
    # тогда поиск без учёта регистра работает и для кириллицы («война» найдёт «Война»).
    dbapi_connection.create_function("lower", 1, _unicode_lower, deterministic=True)


# expire_on_commit=False: после commit() объекты остаются «заполненными», и их можно вернуть из эндпоинта.
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Базовый класс всех ORM-моделей."""


def get_db():
    """Зависимость FastAPI: даёт эндпоинту сессию на время запроса и гарантированно закрывает её."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
