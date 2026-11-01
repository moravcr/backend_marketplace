"""Мини-маркетплейс: API товаров (практика, пара 1) — Шаг 1: каркас и /health."""

from fastapi import FastAPI


app = FastAPI(
    title="Мини-маркетплейс API",
    description="Учебный REST API товаров. Данные хранятся в памяти.",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}
