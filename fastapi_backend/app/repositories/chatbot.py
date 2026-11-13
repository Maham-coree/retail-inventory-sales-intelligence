"""Parameterized persistence and report queries for the retail assistant."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .queries import fetch_rows


def load_catalog(db: Session) -> dict[str, list[dict[str, Any]]]:
    products = fetch_rows(
        db,
        "SELECT p.product_id, p.sku, p.product_name, p.unit_price, p.barcode, "
        "p.supplier_id, c.category_name "
        "FROM retail.products p JOIN retail.categories c USING (category_id) "
        "WHERE p.is_active ORDER BY p.product_name",
    )
    stores = fetch_rows(db, "SELECT store_id, store_name FROM retail.stores ORDER BY store_id")
    return {"products": products, "stores": stores}


def get_availability(
    db: Session, product_id: int, store_id: int | None
) -> list[dict[str, Any]]:
    conditions = "product_id = :product_id"
    params: dict[str, Any] = {"product_id": product_id}
    if store_id is not None:
        conditions += " AND store_id = :store_id"
        params["store_id"] = store_id
    return fetch_rows(
        db,
        "SELECT store_name, product_name, quantity_on_hand, stock_status "
        f"FROM retail.v_stock_status WHERE {conditions} ORDER BY store_name",
        params,
    )


def get_reorder_rows(db: Session, intent: str, role: str) -> list[dict[str, Any]]:
    status_filter = {
        "out_of_stock_list": "priority = 'OUT OF STOCK'",
        "low_stock_list": "priority <> 'OUT OF STOCK'",
        "reorder_list": "TRUE",
    }[intent]
    if role == "cashier":
        columns = "store_name, product_name, quantity_on_hand"
    else:
        columns = (
            "store_name, product_name, supplier_name, quantity_on_hand, "
            "suggested_order_qty, estimated_cost, priority"
        )
    return fetch_rows(
        db,
        f"SELECT {columns} FROM retail.v_reorder_list WHERE {status_filter} "
        "ORDER BY CASE priority WHEN 'OUT OF STOCK' THEN 0 WHEN 'CRITICAL' THEN 1 ELSE 2 END, "
        "store_name, product_name LIMIT 10",
    )


def get_supplier(db: Session, supplier_id: int) -> dict[str, Any] | None:
    row = (
        db.execute(
            text(
                "SELECT supplier_name, city, lead_time_days "
                "FROM retail.suppliers WHERE supplier_id = :supplier_id"
            ),
            {"supplier_id": supplier_id},
        )
        .mappings()
        .first()
    )
    return dict(row) if row is not None else None


def get_open_orders(db: Session) -> list[dict[str, Any]]:
    return fetch_rows(
        db,
        "SELECT po.po_id, po.status, po.order_date, po.expected_date, "
        "s.supplier_name, st.store_name "
        "FROM retail.purchase_orders po "
        "JOIN retail.suppliers s USING (supplier_id) "
        "JOIN retail.stores st USING (store_id) "
        "WHERE po.status IN ('Draft', 'Ordered') "
        "ORDER BY po.order_date DESC, po.po_id DESC LIMIT 10",
    )


def get_sales_summary(db: Session, topic: str) -> list[dict[str, Any]]:
    if topic == "today":
        return fetch_rows(
            db,
            "SELECT sale_day, store_name, total_invoices, total_revenue "
            "FROM retail.v_daily_sales WHERE sale_day = current_date "
            "ORDER BY store_name LIMIT 10",
        )
    if topic == "month":
        return fetch_rows(
            db,
            "SELECT month, total_invoices, total_revenue "
            "FROM retail.v_monthly_revenue "
            "WHERE month = date_trunc('month', current_date)::date LIMIT 10",
        )
    if topic == "top_products":
        return fetch_rows(
            db,
            "SELECT product_name, units_sold, revenue "
            "FROM retail.v_product_performance ORDER BY revenue DESC LIMIT 5",
        )
    if topic == "stores":
        return fetch_rows(
            db,
            "SELECT st.store_name, COALESCE(sum(s.total_amount), 0) AS revenue "
            "FROM retail.stores st LEFT JOIN retail.sales s USING (store_id) "
            "GROUP BY st.store_name ORDER BY revenue DESC, st.store_name LIMIT 10",
        )
    return fetch_rows(
        db,
        "SELECT sale_day, store_name, total_invoices, total_revenue "
        "FROM retail.v_daily_sales WHERE sale_day = current_date "
        "ORDER BY store_name LIMIT 10",
    )


def create_message(
    db: Session, user_id: int, user_message: str, bot_reply: str, intent: str
) -> int:
    return db.execute(
        text(
            "INSERT INTO retail.chat_messages (user_id, user_message, bot_reply, intent) "
            "VALUES (:user_id, :user_message, :bot_reply, :intent) "
            "RETURNING message_id"
        ),
        {
            "user_id": user_id,
            "user_message": user_message,
            "bot_reply": bot_reply,
            "intent": intent,
        },
    ).scalar_one()


def update_feedback(db: Session, user_id: int, message_id: int, helpful: bool) -> bool:
    result = db.execute(
        text(
            "UPDATE retail.chat_messages SET was_helpful = :helpful "
            "WHERE message_id = :message_id AND user_id = :user_id"
        ),
        {"helpful": helpful, "message_id": message_id, "user_id": user_id},
    )
    return result.rowcount == 1


def get_history(db: Session, user_id: int, limit: int) -> list[dict[str, Any]]:
    return fetch_rows(
        db,
        "SELECT message_id, user_message, bot_reply, intent, was_helpful, created_at "
        "FROM (SELECT message_id, user_message, bot_reply, intent, was_helpful, created_at "
        "FROM retail.chat_messages WHERE user_id = :user_id "
        "ORDER BY created_at DESC, message_id DESC LIMIT :limit) recent "
        "ORDER BY created_at, message_id",
        {"user_id": user_id, "limit": limit},
    )


def get_chatbot_stats(db: Session) -> dict[str, Any]:
    totals = db.execute(
        text(
            "SELECT count(*) AS total_messages, "
            "count(*) FILTER (WHERE intent = 'fallback') AS unanswered_messages, "
            "count(*) FILTER (WHERE was_helpful IS NOT NULL) AS feedback_count, "
            "count(*) FILTER (WHERE was_helpful IS TRUE) AS helpful_count "
            "FROM retail.chat_messages"
        )
    ).mappings().one()
    intents = fetch_rows(
        db,
        "SELECT intent, count(*) AS count FROM retail.chat_messages "
        "GROUP BY intent ORDER BY count DESC, intent",
    )
    total = int(totals["total_messages"])
    feedback_count = int(totals["feedback_count"])
    return {
        "total_messages": total,
        "unanswered_messages": int(totals["unanswered_messages"]),
        "unanswered_share": (
            float(totals["unanswered_messages"]) / total if total else 0.0
        ),
        "helpful_rate": (
            float(totals["helpful_count"]) / feedback_count if feedback_count else None
        ),
        "intents": intents,
    }
