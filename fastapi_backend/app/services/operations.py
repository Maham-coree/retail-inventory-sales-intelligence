"""Core business operations that coordinate validated requests and SQL persistence."""

from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..schemas import InventoryAdjust, SaleCreate


def insert_sale(db: Session, data: SaleCreate, employee_id: int) -> int:
    sale_id = db.execute(
        text(
            "INSERT INTO retail.sales "
            "(store_id, customer_id, employee_id, payment_method) "
            "VALUES (:store, :customer, :employee, :payment) RETURNING sale_id"
        ),
        {
            "store": data.store_id,
            "customer": data.customer_id,
            "employee": employee_id,
            "payment": data.payment_method,
        },
    ).scalar_one()
    for line in data.items:
        price = db.execute(
            text("SELECT unit_price FROM retail.products WHERE product_id=:product"),
            {"product": line.product_id},
        ).scalar_one_or_none()
        if price is None:
            raise HTTPException(404, f"Product {line.product_id} not found")
        db.execute(
            text(
                "INSERT INTO retail.sale_items "
                "(sale_id, product_id, quantity, unit_price, discount) "
                "VALUES (:sale, :product, :quantity, :price, :discount)"
            ),
            {
                "sale": sale_id,
                "product": line.product_id,
                "quantity": line.quantity,
                "price": price,
                "discount": line.discount,
            },
        )
    return sale_id


def adjust_stock(db: Session, data: InventoryAdjust) -> None:
    db.execute(
        text("CALL retail.sp_adjust_stock(:store, :product, :delta, :reason)"),
        {
            "store": data.store_id,
            "product": data.product_id,
            "delta": data.delta,
            "reason": data.reason,
        },
    )
    db.commit()


def receive_order(db: Session, po_id: int) -> None:
    db.execute(text("SELECT retail.receive_purchase_order(:po)"), {"po": po_id})
    db.commit()


def create_draft_orders(db: Session, alerts: list[dict[str, Any]]) -> list[int]:
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for alert in alerts:
        grouped.setdefault((alert["supplier_id"], alert["store_id"]), []).append(alert)
    created: list[int] = []
    for (supplier_id, store_id), items in grouped.items():
        po_id = db.execute(
            text(
                "INSERT INTO retail.purchase_orders (supplier_id, store_id) "
                "VALUES (:supplier, :store) RETURNING po_id"
            ),
            {"supplier": supplier_id, "store": store_id},
        ).scalar_one()
        for item in items:
            db.execute(
                text(
                    "INSERT INTO retail.purchase_order_items "
                    "(po_id, product_id, quantity, unit_cost) "
                    "VALUES (:po, :product, :qty, :cost)"
                ),
                {
                    "po": po_id,
                    "product": item["product_id"],
                    "qty": item["reorder_quantity"],
                    "cost": item["unit_cost"],
                },
            )
        created.append(po_id)
    db.commit()
    return created
