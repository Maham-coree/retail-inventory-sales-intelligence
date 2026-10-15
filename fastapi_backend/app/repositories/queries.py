"""Small parameterized query helpers for repository and service code."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def fetch_rows(
    db: Session, statement: str, params: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    return [dict(row) for row in db.execute(text(statement), params or {}).mappings().all()]


def fetch_one(
    db: Session, statement: str, params: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    row = db.execute(text(statement), params or {}).mappings().first()
    return dict(row) if row is not None else None
