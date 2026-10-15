"""Inventory, sales, purchase-order, ledger, dashboard, and report APIs."""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import get_current_user, require_roles
from ..reports import REPORTS
from ..repositories.queries import fetch_rows
from ..services.operations import (
    adjust_stock as adjust_stock_service,
)
from ..services.operations import (
    create_draft_orders,
    insert_sale,
    receive_order,
)
from .resources import db_error

router = APIRouter(tags=["inventory and sales"])


def _query_rows(
    db: Session, sql: str, params: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    return fetch_rows(db, sql, params)


@router.get("/reorder-alerts", summary="List current reorder alerts")
def reorder_alerts(
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return _query_rows(db, "SELECT * FROM retail.v_reorder_list")


@router.get("/stock", summary="List stock status by store")
def stock_status(
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return _query_rows(
        db,
        "SELECT * FROM retail.v_stock_status ORDER BY store_name, product_name",
    )


@router.get("/inventory", summary="Filter stock by store, product, or status")
def inventory(
    store_id: int | None = None,
    product_id: int | None = None,
    stock_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    conditions = []
    params: dict[str, Any] = {}
    for column, value in (
        ("store_id", store_id),
        ("product_id", product_id),
        ("stock_status", stock_status),
    ):
        if value is not None:
            conditions.append(f"{column} = :{column}")
            params[column] = value
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    return _query_rows(
        db,
        "SELECT * FROM retail.v_stock_status" + where + " ORDER BY store_name, product_name",
        params,
    )


@router.post("/inventory/adjust", summary="Adjust stock through the stored procedure")
def adjust_inventory(
    data: schemas.InventoryAdjust,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_roles("admin", "manager")),
) -> dict[str, str]:
    try:
        adjust_stock_service(db, data)
    except DBAPIError as exc:
        db.rollback()
        original = exc.orig
        code = getattr(original, "sqlstate", None)
        if code == "23514":
            raise HTTPException(409, "Stock adjustment would result in negative inventory") from exc
        raise HTTPException(400, "Stock adjustment failed") from exc
    return {"message": "Inventory adjusted"}


@router.get("/sales", summary="List sales")
def list_sales(
    search: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    sort: str = "sale_id",
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(get_current_user),
) -> Any:
    allowed_sort = {"sale_id", "sale_date", "total_amount"}
    if sort not in allowed_sort:
        raise HTTPException(422, "Unsupported sales sort field")
    where = []
    params: dict[str, Any] = {}
    if user["role"] == "cashier":
        where.append("s.employee_id = :employee_id")
        params["employee_id"] = user["employee_id"]
    if search:
        where.append("(CAST(s.sale_id AS text) ILIKE :search OR c.full_name ILIKE :search)")
        params["search"] = f"%{search}%"
    predicate = " WHERE " + " AND ".join(where) if where else ""
    base = (
        "SELECT s.sale_id AS invoice, st.store_name AS store, "
        "COALESCE(c.full_name, 'Walk-in') AS customer, e.full_name AS cashier, "
        "CAST(s.sale_date AS date) AS date, s.payment_method AS payment, "
        "s.total_amount AS total FROM retail.sales s "
        "JOIN retail.stores st ON st.store_id=s.store_id "
        "JOIN retail.employees e ON e.employee_id=s.employee_id "
        "LEFT JOIN retail.customers c ON c.customer_id=s.customer_id"
    )
    if page is None:
        return _query_rows(db, base + predicate + f" ORDER BY s.{sort} DESC", params)
    count = db.execute(
        text(
            "SELECT count(*) FROM retail.sales s "
            "LEFT JOIN retail.customers c ON c.customer_id=s.customer_id" + predicate
        ),
        params,
    ).scalar_one()
    params.update({"limit": page_size, "offset": (page - 1) * page_size})
    rows = _query_rows(
        db,
        base + predicate + f" ORDER BY s.{sort} DESC LIMIT :limit OFFSET :offset",
        params,
    )
    return {"items": rows, "total": count, "page": page, "page_size": page_size}


@router.post("/sales", status_code=201, summary="Create a sale and its sale lines")
def create_sale(
    data: schemas.SaleCreate,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(get_current_user),
) -> dict[str, Any]:
    employee_id = data.employee_id or user.get("employee_id")
    if employee_id is None:
        raise HTTPException(422, "An employee must be associated with this sale")
    if user["role"] == "cashier" and employee_id != user["employee_id"]:
        raise HTTPException(403, "Cashiers may only create sales for themselves")
    try:
        sale_id = insert_sale(db, data, employee_id)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except (IntegrityError, DBAPIError) as exc:
        db.rollback()
        mapped = db_error(exc) if isinstance(exc, IntegrityError) else None
        if mapped is not None and mapped.status_code == 409:
            raise mapped from exc
        if getattr(exc.orig, "sqlstate", None) == "23514":
            raise HTTPException(409, "Insufficient stock for one or more products") from exc
        if mapped is not None:
            raise mapped from exc
        raise HTTPException(409, "Sale could not be completed") from exc
    return get_sale(sale_id, db, user)


@router.get("/sales/{sale_id}", summary="Get a sale and receipt lines")
def get_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(get_current_user),
) -> dict[str, Any]:
    sale = (
        db.execute(
            text(
                "SELECT s.*, st.store_name, c.full_name AS customer_name, "
                "e.full_name AS employee_name FROM retail.sales s "
                "JOIN retail.stores st ON st.store_id=s.store_id "
                "LEFT JOIN retail.customers c ON c.customer_id=s.customer_id "
                "JOIN retail.employees e ON e.employee_id=s.employee_id "
                "WHERE s.sale_id=:sale"
            ),
            {"sale": sale_id},
        )
        .mappings()
        .first()
    )
    if sale is None:
        raise HTTPException(404, "Sale not found")
    if user["role"] == "cashier" and sale["employee_id"] != user["employee_id"]:
        raise HTTPException(403, "Cashiers may only view their own sales")
    lines = _query_rows(
        db,
        "SELECT si.sale_item_id, si.product_id, p.sku, p.product_name, "
        "si.quantity, si.unit_price, si.discount, si.line_total "
        "FROM retail.sale_items si JOIN retail.products p ON p.product_id=si.product_id "
        "WHERE si.sale_id=:sale ORDER BY si.sale_item_id",
        {"sale": sale_id},
    )
    return {"sale": dict(sale), "items": lines}


@router.get("/purchase-orders", summary="List purchase orders")
def list_purchase_orders(
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_roles("admin", "manager")),
) -> list[dict[str, Any]]:
    return _query_rows(db, "SELECT * FROM retail.purchase_orders ORDER BY po_id DESC")


@router.post("/purchase-orders", status_code=201, summary="Create purchase order")
def create_purchase_order(
    data: schemas.PurchaseOrderCreate,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_roles("admin", "manager")),
) -> dict[str, Any]:
    try:
        po_id = db.execute(
            text(
                "INSERT INTO retail.purchase_orders (supplier_id, store_id, expected_date) "
                "VALUES (:supplier, :store, :expected) RETURNING po_id"
            ),
            {
                "supplier": data.supplier_id,
                "store": data.store_id,
                "expected": data.expected_date,
            },
        ).scalar_one()
        for item in data.items:
            db.execute(
                text(
                    "INSERT INTO retail.purchase_order_items "
                    "(po_id, product_id, quantity, unit_cost) "
                    "VALUES (:po, :product, :quantity, :cost)"
                ),
                {
                    "po": po_id,
                    "product": item.product_id,
                    "quantity": item.quantity,
                    "cost": item.unit_cost,
                },
            )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise db_error(exc) from exc
    return get_purchase_order(po_id, db)


@router.get("/purchase-orders/{po_id}", summary="Get purchase order and lines")
def get_purchase_order(
    po_id: int,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_roles("admin", "manager")),
) -> dict[str, Any]:
    order = (
        db.execute(
            text("SELECT * FROM retail.purchase_orders WHERE po_id=:po"),
            {"po": po_id},
        )
        .mappings()
        .first()
    )
    if order is None:
        raise HTTPException(404, "Purchase order not found")
    return {
        "order": dict(order),
        "items": _query_rows(
            db,
            "SELECT poi.*, p.sku, p.product_name FROM retail.purchase_order_items poi "
            "JOIN retail.products p ON p.product_id=poi.product_id WHERE poi.po_id=:po",
            {"po": po_id},
        ),
    }


@router.patch("/purchase-orders/{po_id}/status", summary="Change purchase-order status")
def change_purchase_order_status(
    po_id: int,
    new_status: str = Query(pattern="^(Draft|Ordered|Cancelled)$"),
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_roles("admin", "manager")),
) -> dict[str, Any]:
    row = (
        db.execute(
            text(
                "UPDATE retail.purchase_orders SET status=:status WHERE po_id=:po "
                "AND status <> 'Received' RETURNING *"
            ),
            {"status": new_status, "po": po_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        db.rollback()
        raise HTTPException(404, "Purchase order not found or already received")
    db.commit()
    return dict(row)


@router.post("/purchase-orders/{po_id}/receive", summary="Receive a purchase order")
def receive_purchase_order(
    po_id: int,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_roles("admin", "manager")),
) -> dict[str, str]:
    try:
        receive_order(db, po_id)
    except DBAPIError as exc:
        db.rollback()
        raise HTTPException(409, "Purchase order cannot be received") from exc
    return {"message": f"Purchase order {po_id} received"}


@router.post(
    "/purchase-orders/from-reorder-alerts",
    summary="Create draft purchase orders from reorder alerts",
)
def create_pos_from_reorder(
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_roles("admin", "manager")),
) -> dict[str, Any]:
    alerts = _query_rows(
        db,
        "SELECT i.store_id, p.supplier_id, i.product_id, p.reorder_quantity, p.unit_cost "
        "FROM retail.inventory i JOIN retail.products p ON p.product_id=i.product_id "
        "WHERE p.is_active AND i.quantity_on_hand <= p.reorder_level "
        "AND NOT EXISTS (SELECT 1 FROM retail.purchase_order_items poi "
        "JOIN retail.purchase_orders po ON po.po_id=poi.po_id "
        "WHERE po.store_id=i.store_id AND poi.product_id=i.product_id "
        "AND po.status IN ('Draft','Ordered'))",
    )
    try:
        created = create_draft_orders(db, alerts)
    except DBAPIError:
        db.rollback()
        raise
    return {"created_po_ids": created}


@router.get("/stock-movements", summary="Browse the stock movement ledger")
def stock_movements(
    product_id: int | None = None,
    store_id: int | None = None,
    movement_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    sort: str = "created_at",
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_roles("admin", "manager")),
) -> dict[str, Any]:
    sort_columns = {
        "created_at": "sm.created_at",
        "movement_id": "sm.movement_id",
        "quantity": "sm.quantity",
        "movement_type": "sm.movement_type",
    }
    if sort not in sort_columns:
        raise HTTPException(422, "Unsupported stock movement sort field")
    clauses = []
    params: dict[str, Any] = {}
    for name, value in (
        ("product_id", product_id),
        ("store_id", store_id),
        ("movement_type", movement_type),
    ):
        if value is not None:
            clauses.append(f"sm.{name} = :{name}")
            params[name] = value
    if date_from is not None:
        clauses.append("sm.created_at >= :date_from")
        params["date_from"] = date_from
    if date_to is not None:
        clauses.append("sm.created_at < :date_to + interval '1 day'")
        params["date_to"] = date_to
    if search:
        clauses.append(
            "(sm.reference ILIKE :search OR p.sku ILIKE :search OR p.product_name ILIKE :search)"
        )
        params["search"] = f"%{search}%"
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    total = db.execute(
        text(
            "SELECT count(*) FROM retail.stock_movements sm "
            "JOIN retail.products p ON p.product_id=sm.product_id" + where
        ),
        params,
    ).scalar_one()
    params.update({"limit": page_size, "offset": (page - 1) * page_size})
    rows = _query_rows(
        db,
        "SELECT sm.*, s.store_name, p.sku, p.product_name "
        "FROM retail.stock_movements sm "
        "JOIN retail.stores s ON s.store_id=sm.store_id "
        "JOIN retail.products p ON p.product_id=sm.product_id"
        + where
        + f" ORDER BY {sort_columns[sort]} DESC, sm.movement_id DESC "
        "LIMIT :limit OFFSET :offset",
        params,
    )
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


@router.get("/summary", summary="Get existing retail KPIs")
def summary(
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(get_current_user),
) -> dict[str, Any]:
    return {
        "total_sales": db.execute(
            text("SELECT COALESCE(SUM(total_amount), 0) FROM retail.sales")
        ).scalar_one(),
        "invoices": db.execute(text("SELECT count(*) FROM retail.sales")).scalar_one(),
        "stock_value": db.execute(
            text(
                "SELECT COALESCE(SUM(i.quantity_on_hand*p.unit_cost), 0) "
                "FROM retail.inventory i JOIN retail.products p USING(product_id)"
            )
        ).scalar_one(),
        "to_reorder": db.execute(text("SELECT count(*) FROM retail.v_reorder_list")).scalar_one(),
        "out_of_stock": db.execute(
            text("SELECT count(*) FROM retail.v_reorder_list WHERE priority='OUT OF STOCK'")
        ).scalar_one(),
    }


@router.get("/dashboard/summary", summary="Get dashboard KPIs and charts")
def dashboard_summary(
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(get_current_user),
) -> dict[str, Any]:
    daily = _query_rows(
        db,
        "SELECT sale_date::date AS day, SUM(total_amount) AS revenue "
        "FROM retail.sales WHERE sale_date >= current_date - interval '29 days' "
        "GROUP BY sale_date::date ORDER BY day",
    )
    top = _query_rows(
        db,
        "SELECT product_name, revenue FROM retail.v_product_performance "
        "ORDER BY revenue DESC LIMIT 5",
    )
    status_counts = _query_rows(
        db,
        "SELECT stock_status, count(*) AS count FROM retail.v_stock_status "
        "GROUP BY stock_status ORDER BY stock_status",
    )
    store_revenue = _query_rows(
        db,
        "SELECT st.store_name, COALESCE(sum(s.total_amount),0) AS revenue "
        "FROM retail.stores st LEFT JOIN retail.sales s USING(store_id) "
        "GROUP BY st.store_name ORDER BY st.store_name",
    )
    return {
        **summary(db),
        "sales_per_day": daily,
        "top_products": top,
        "stock_status_counts": status_counts,
        "revenue_per_store": store_revenue,
    }


@router.get("/reports", summary="List predefined relational and SQL reports")
def list_reports(
    _: dict[str, object] = Depends(get_current_user),
) -> list[dict[str, str]]:
    return [
        {key: report[key] for key in ("id", "group", "title", "algebra", "sql")}
        for report in REPORTS
    ]


@router.get("/reports/{report_id}", summary="Run a predefined report")
def run_report(
    report_id: str,
    explain: bool = False,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(get_current_user),
) -> dict[str, Any]:
    report = next((item for item in REPORTS if item["id"] == report_id), None)
    if report is None:
        raise HTTPException(404, "Report not found")
    if explain:
        plan = db.execute(text("EXPLAIN " + report["sql"])).all()
        return {"plan": [row[0] for row in plan]}
    result = db.execute(text(report["sql"]))
    return {"columns": list(result.keys()), "rows": [list(row) for row in result.all()]}


@router.post("/reports/materialized/refresh", summary="Refresh the monthly sales materialized view")
def refresh_monthly_sales(
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_roles("admin", "manager")),
) -> dict[str, str]:
    try:
        db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY retail.mv_monthly_sales"))
        db.commit()
    except DBAPIError as exc:
        db.rollback()
        raise HTTPException(409, "Monthly sales view refresh failed") from exc
    return {"message": "Monthly sales view refreshed"}
