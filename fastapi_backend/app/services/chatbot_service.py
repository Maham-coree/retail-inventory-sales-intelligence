"""Intent handling and safe response construction for the retail assistant."""

import json
import logging
import time
from decimal import Decimal
from pathlib import Path
from threading import Lock
from typing import Any

import httpx
from sqlalchemy.orm import Session

from .. import schemas
from ..chatbot.nlp import detect_intent, match_names, normalize_text, redact_sensitive_text
from ..config import settings
from ..repositories import chatbot as chatbot_repository
from ..schemas import ChatbotContext

logger = logging.getLogger(__name__)
_GUIDES = json.loads(Path(__file__).parents[1].joinpath("chatbot", "knowledge_base.json").read_text(
    encoding="utf-8"
))
_CATALOG_LOCK = Lock()
_CATALOG: dict[str, list[dict[str, Any]]] | None = None
_CATALOG_EXPIRES_AT = 0.0
ALL_ROLES = ("admin", "manager", "cashier")
INTENT_ROLES = {
    "greeting": ALL_ROLES,
    "help": ALL_ROLES,
    "product_availability": ALL_ROLES,
    "product_price": ALL_ROLES,
    "out_of_stock_list": ALL_ROLES,
    "low_stock_list": ALL_ROLES,
    "reorder_list": ALL_ROLES,
    "sales_summary": ("admin", "manager"),
    "supplier_info": ("admin", "manager"),
    "purchase_orders_status": ("admin", "manager"),
    "how_to": ALL_ROLES,
    "troubleshooting": ALL_ROLES,
    "role_permissions": ALL_ROLES,
    "fallback": ALL_ROLES,
}
ROLE_SUGGESTIONS = {
    "cashier": [
        "Is milk in stock?",
        "What is the price of Basmati Rice?",
        "How do I record a sale?",
        "Show me low-stock items",
        "What can my role do?",
    ],
    "manager": [
        "Show sales today",
        "Which products need reordering?",
        "What purchase orders are open?",
        "How do I adjust stock?",
        "Show revenue per store",
    ],
    "admin": [
        "Show sales today",
        "Which products need reordering?",
        "What purchase orders are open?",
        "How do I reset a user's password?",
        "What can my role do?",
    ],
}
FALLBACK_SUGGESTIONS = [
    "How do I check stock?",
    "Show sales today",
    "How do I record a sale?",
    "What can my role do?",
]


def get_suggestions(role: str) -> list[str]:
    return list(ROLE_SUGGESTIONS.get(role, FALLBACK_SUGGESTIONS))


def _catalog(db: Session) -> dict[str, list[dict[str, Any]]]:
    global _CATALOG, _CATALOG_EXPIRES_AT
    with _CATALOG_LOCK:
        if _CATALOG is not None and time.monotonic() < _CATALOG_EXPIRES_AT:
            return _CATALOG
        _CATALOG = chatbot_repository.load_catalog(db)
        _CATALOG_EXPIRES_AT = time.monotonic() + 60
        return _CATALOG


def _table(rows: list[dict[str, Any]], columns: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "table",
        "columns": columns or (list(rows[0]) if rows else []),
        "rows": rows[:10],
    }


def _list(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "list", "rows": rows[:10]}


def _guide_score(message: str, guide: dict[str, Any]) -> int:
    normalized = normalize_text(message)
    words = set(normalized.split())
    return max(
        (
            2 if normalize_text(keyword) in normalized
            else len(words.intersection(normalize_text(keyword).split()))
            for keyword in guide["keywords"]
        ),
        default=0,
    )


def _find_guide(
    message: str, role: str, minimum_score: int = 1
) -> dict[str, Any] | None:
    choices = [
        guide for guide in _GUIDES
        if role in guide["roles"] and _guide_score(message, guide) >= minimum_score
    ]
    return max(choices, key=lambda guide: _guide_score(message, guide), default=None)


def _choose_product(
    message: str, products: list[dict[str, Any]], context: ChatbotContext
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    matched = match_names(message, products)
    normalized = normalize_text(message)
    ordinal = 2 if "second" in normalized or "2nd" in normalized else 1
    if "third" in normalized or "3rd" in normalized:
        ordinal = 3
    if context.candidate_product_ids and any(
        word in normalized for word in ("first", "1st", "second", "2nd", "third", "3rd")
    ):
        candidates = [
            product for product in products
            if product["product_id"] in context.candidate_product_ids
        ]
        if len(candidates) >= ordinal:
            return candidates[ordinal - 1], []
    if len(matched) == 1:
        return matched[0], []
    if len(matched) > 1:
        return None, matched
    if context.product_id is not None:
        contextual = next(
            (product for product in products if product["product_id"] == context.product_id),
            None,
        )
        if contextual is not None:
            return contextual, []
    return None, []


def _choose_store(
    message: str, stores: list[dict[str, Any]], context: ChatbotContext
) -> dict[str, Any] | None:
    normalized = normalize_text(message)
    message_words = set(normalized.split())
    matched = [
        store
        for store in stores
        if normalize_text(str(store["store_name"])) in normalized
        or message_words.intersection(normalize_text(str(store["store_name"])).split())
    ]
    if len(matched) == 1:
        return matched[0]
    if "second store" in normalized or "2nd store" in normalized:
        return stores[1] if len(stores) > 1 else None
    if "third store" in normalized or "3rd store" in normalized:
        return stores[2] if len(stores) > 2 else None
    if "other store" in normalized and context.store_id is not None:
        return next((store for store in stores if store["store_id"] != context.store_id), None)
    if context.store_id is not None:
        return next((store for store in stores if store["store_id"] == context.store_id), None)
    return None


def _product_ambiguity(
    intent: str, matches: list[dict[str, Any]]
) -> tuple[str, dict[str, Any], list[str]]:
    names = [str(product["product_name"]) for product in matches[:5]]
    reply = "I found a few matching products. Choose one: " + ", ".join(names) + "."
    suggestions = names[:5]
    return reply, {
        "intent": intent,
        "candidate_product_ids": [int(item["product_id"]) for item in matches[:5]],
    }, suggestions


def _sales_topic(message: str) -> str:
    normalized = normalize_text(message)
    if any(word in normalized.split() for word in ("today", "aaj")):
        return "today"
    if any(word in normalized.split() for word in ("month", "monthly", "maheena")):
        return "month"
    if any(word in normalized.split() for word in ("top", "best", "selling")):
        return "top_products"
    if any(word in normalized.split() for word in ("store", "branch")):
        return "stores"
    return "overview"


def _sales_overview(db: Session) -> dict[str, Any]:
    today_rows = chatbot_repository.get_sales_summary(db, "today")
    month_rows = chatbot_repository.get_sales_summary(db, "month")
    top_rows = chatbot_repository.get_sales_summary(db, "top_products")
    store_rows = chatbot_repository.get_sales_summary(db, "stores")
    today_revenue = sum((row["total_revenue"] or 0 for row in today_rows), Decimal("0"))
    today_invoices = sum((row["total_invoices"] or 0 for row in today_rows), 0)
    month_revenue = month_rows[0]["total_revenue"] if month_rows else Decimal("0")
    month_invoices = month_rows[0]["total_invoices"] if month_rows else 0
    rows: list[dict[str, Any]] = [
        {"section": "Today", "name": "All stores", "revenue": today_revenue, "invoices": today_invoices},
        {"section": "This month", "name": "All stores", "revenue": month_revenue, "invoices": month_invoices},
    ]
    rows.extend(
        {"section": "Top product", "name": item["product_name"], "revenue": item["revenue"], "units": item["units_sold"]}
        for item in top_rows[:3]
    )
    rows.extend(
        {"section": "Store revenue", "name": item["store_name"], "revenue": item["revenue"]}
        for item in store_rows[:3]
    )
    return {
        "reply": "Here is the sales overview, including today, this month, top products, and revenue per store.",
        "data": _table(rows, ["section", "name", "revenue", "invoices", "units"]),
    }


def _role_permission_reply(role: str) -> str:
    if role == "cashier":
        return (
            "As a cashier, you can view products and stock, manage customers, and record sales. "
            "You cannot access reports, user administration, developer labs, or stock/order controls."
        )
    if role == "manager":
        return (
            "As a manager, you can manage business records, adjust inventory, manage purchase orders, "
            "record sales, and view reports. User administration and developer labs are admin-only."
        )
    return (
        "As an admin, you have the manager capabilities plus user administration and the developer labs."
    )


def _llm_fallback(message: str, guide: dict[str, Any] | None) -> str | None:
    if not settings.chatbot_llm_enabled or guide is None:
        return None
    endpoint = settings.chatbot_llm_base_url.rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint += "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.chatbot_llm_api_key}"} if settings.chatbot_llm_api_key else {}
    payload = {
        "model": settings.chatbot_llm_model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Answer in simple English only about this retail system. Use only this guide; "
                    "if it does not answer the question, say you do not know.\n\n"
                    f"Guide: {guide['answer']}"
                ),
            },
            {"role": "user", "content": redact_sensitive_text(message)},
        ],
    }
    try:
        response = httpx.post(endpoint, headers=headers, json=payload, timeout=8.0)
        response.raise_for_status()
        answer = response.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
        logger.warning("Optional chatbot LLM fallback failed; using local suggestions")
        return None
    return answer.strip()[:4000] if isinstance(answer, str) and answer.strip() else None


def handle_message(
    db: Session,
    user: dict[str, Any],
    request: schemas.ChatbotMessageRequest,
) -> dict[str, Any]:
    message = request.message.strip()
    role = str(user["role"])
    context = request.context
    catalog = _catalog(db)
    products, stores = catalog["products"], catalog["stores"]
    intent = detect_intent(message)
    normalized = normalize_text(message)
    if (
        intent is None
        and context.intent == "product_availability"
        and any(word in normalized for word in ("second", "2nd", "third", "3rd", "other"))
    ):
        intent = "product_availability"
    if intent is None:
        intent = "fallback"

    suggestions = get_suggestions(role)
    data: dict[str, Any] | None = None
    new_context = context.model_dump(exclude_none=True)
    new_context["intent"] = intent

    if role not in INTENT_ROLES.get(intent, ALL_ROLES):
        reply = (
            "Your role cannot view or change that information. "
            "You can ask about product availability, stock statuses, or system guides."
        )
        suggestions = get_suggestions(role)[:4]
    elif intent == "greeting":
        reply = "Hello! I can help with stock, products, sales, purchase orders, and step-by-step system guides."
    elif intent == "help":
        reply = (
            "I can answer questions about products and stock, show role-authorized sales and reorder data, "
            "and explain how to use the real pages in this system."
        )
    elif intent == "role_permissions":
        reply = _role_permission_reply(role)
    elif intent in {"how_to", "troubleshooting"}:
        guide = _find_guide(message, role)
        if guide is None:
            reply = "I could not find a matching guide. Please describe the page or error you need help with."
        else:
            reply = guide["answer"]
            suggestions = list(guide["follow_ups"])[:5]
    elif intent in {"product_availability", "product_price", "supplier_info"}:
        product, matches = _choose_product(message, products, context)
        if product is None and matches:
            reply, new_context, suggestions = _product_ambiguity(intent, matches)
        elif product is None:
            reply = "Which product do you mean? Please include its name or SKU."
            suggestions = ["Show me products", "How do I search for a product?"]
        elif intent == "product_availability":
            store = _choose_store(message, stores, context)
            rows = chatbot_repository.get_availability(
                db, int(product["product_id"]), int(store["store_id"]) if store else None
            )
            reply = (
                f"{product['product_name']} stock by store:"
                if rows
                else f"{product['product_name']} is not listed in the selected store."
            )
            data = _table(rows, ["store_name", "product_name", "quantity_on_hand", "stock_status"])
            new_context.update(
                {
                    "product_id": int(product["product_id"]),
                    "product_name": str(product["product_name"]),
                }
            )
            if store:
                new_context.update({"store_id": int(store["store_id"]), "store_name": store["store_name"]})
        elif intent == "product_price":
            row = {
                key: product.get(key)
                for key in ("product_name", "sku", "unit_price", "category_name", "barcode")
            }
            reply = f"The listed price for {product['product_name']} is {product['unit_price']}."
            data = _table([row], ["product_name", "sku", "unit_price", "category_name", "barcode"])
            new_context.update(
                {
                    "product_id": int(product["product_id"]),
                    "product_name": str(product["product_name"]),
                }
            )
        else:
            supplier = chatbot_repository.get_supplier(db, int(product["supplier_id"]))
            if supplier is None:
                reply = f"No supplier record was found for {product['product_name']}."
            else:
                reply = (
                    f"{supplier['supplier_name']} supplies {product['product_name']}; "
                    f"lead time is {supplier['lead_time_days']} days."
                )
                data = _table([{"product_name": product["product_name"], **supplier}])
    elif intent in {"out_of_stock_list", "low_stock_list", "reorder_list"}:
        rows = chatbot_repository.get_reorder_rows(db, intent, role)
        reply = f"Here are up to 10 {intent.replace('_', ' ')} records."
        data = _table(rows)
    elif intent == "sales_summary":
        topic = _sales_topic(message)
        if topic == "overview":
            overview = _sales_overview(db)
            reply, data = overview["reply"], overview["data"]
        else:
            rows = chatbot_repository.get_sales_summary(db, topic)
            labels = {
                "today": "today's sales",
                "month": "this month's sales",
                "top_products": "top products by revenue",
                "stores": "revenue per store",
            }
            reply = f"Here is {labels[topic]}."
            data = _table(rows)
    elif intent == "purchase_orders_status":
        rows = chatbot_repository.get_open_orders(db)
        reply = "Here are the open purchase orders (Draft or Ordered)."
        data = _table(rows)
    elif intent == "fallback":
        guide = _find_guide(message, role, minimum_score=2)
        answer = _llm_fallback(message, guide)
        reply = answer or (
            "I did not understand that question. I can help with this retail system; "
            "for anything outside it, please contact your admin."
        )
        suggestions = FALLBACK_SUGGESTIONS[:4]
    else:
        reply = "I could not answer that. Please try a system guide or contact your admin."

    reply = reply[:4000]
    message_id = chatbot_repository.create_message(
        db,
        int(user["user_id"]),
        redact_sensitive_text(message),
        reply,
        intent,
    )
    return {
        "reply": reply,
        "intent": intent,
        "data": data,
        "suggestions": suggestions[:5],
        "context": new_context,
        "message_id": message_id,
    }
