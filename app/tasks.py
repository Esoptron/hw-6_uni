from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.cache import cache
from app.database import SessionLocal
from app.models import Product


def _read_price(row: dict[str, str]) -> float:
    raw = row.get("price") or row.get("цена") or "0"
    return float(raw.replace(",", "."))


def _read_name(row: dict[str, str]) -> str:
    name = row.get("name") or row.get("title") or row.get("название") or row.get("имя")
    if not name:
        raise ValueError("CSV row does not contain a name/title column")
    return name.strip()


def import_products_from_csv(csv_path: str) -> None:
    """Background task that imports product rows from a CSV file into the DB."""

    path = Path(csv_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file, SessionLocal() as db:
        reader = csv.DictReader(file)
        products = [
            Product(
                name=_read_name(row),
                description=(row.get("description") or row.get("описание") or None),
                price=_read_price(row),
            )
            for row in reader
        ]
        if products:
            db.add_all(products)
            db.commit()
    cache.invalidate_products()


def delete_products_by_ids(ids: list[int]) -> None:
    """Background task that deletes product rows by identifiers."""

    with SessionLocal() as db:
        db: Session
        db.execute(delete(Product).where(Product.id.in_(ids)))
        db.commit()
    cache.invalidate_products()
