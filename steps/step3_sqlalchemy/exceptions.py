"""Доменные ошибки. Слой данных не знает про HTTP: он говорит «не найдено» или «конфликт»,
а превратить это в 404/409 — задача main.py."""


class AppError(Exception):
    status_code = 400

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.message = message
        self.field = field


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class BadRequestError(AppError):
    status_code = 400
