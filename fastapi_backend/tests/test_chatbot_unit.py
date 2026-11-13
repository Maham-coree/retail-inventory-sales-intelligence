"""Database-independent tests for assistant language and validation helpers."""

import pytest
from pydantic import ValidationError

from app.chatbot.nlp import detect_intent, match_names, normalize_text, redact_sensitive_text
from app.schemas import ChatbotMessageRequest
from app.services.chatbot_service import INTENT_ROLES, get_suggestions


def test_normalize_text_handles_punctuation_and_roman_urdu() -> None:
    assert normalize_text("  Kitna STOCK hai?! ") == "kitna stock hai"


@pytest.mark.parametrize(
    ("message", "intent"),
    [
        ("Hello assistant", "greeting"),
        ("madad please", "help"),
        ("stock of Basmati Rice", "product_availability"),
        ("milk ka qeemat", "product_price"),
        ("show out of stock items", "out_of_stock_list"),
        ("what is low stock", "low_stock_list"),
        ("what should we reorder", "reorder_list"),
        ("sales today", "sales_summary"),
        ("lead time for supplier", "supplier_info"),
        ("what purchase orders are open", "purchase_orders_status"),
        ("how do I record a sale", "how_to"),
        ("why was my sale rejected", "troubleshooting"),
        ("what can my role do", "role_permissions"),
        ("kitna stock hai", "product_availability"),
    ],
)
def test_detect_intent_for_common_english_and_roman_urdu(
    message: str, intent: str
) -> None:
    assert detect_intent(message) == intent


def test_fuzzy_product_matching_finds_partial_product_names() -> None:
    products = [
        {"product_id": 1, "product_name": "Basmati Rice 5kg", "sku": "GRC-001"},
        {"product_id": 2, "product_name": "Fresh Milk 1L", "sku": "DRY-001"},
    ]
    assert match_names("stock of basmati rice", products)[0]["product_id"] == 1
    assert match_names("kitna stock milk", products)[0]["product_id"] == 2


def test_intent_permissions_and_suggestions_are_role_aware() -> None:
    assert "cashier" not in INTENT_ROLES["sales_summary"]
    assert "manager" in INTENT_ROLES["sales_summary"]
    assert any("stock" in item.lower() for item in get_suggestions("cashier"))
    assert any("sales" in item.lower() for item in get_suggestions("manager"))


def test_chatbot_message_validation_and_secret_redaction() -> None:
    with pytest.raises(ValidationError):
        ChatbotMessageRequest(message="x" * 501)
    with pytest.raises(ValidationError):
        ChatbotMessageRequest(message="hello", context={"unknown": "value"})
    assert redact_sensitive_text("my password=hidden Bearer abc.def") == (
        "my password=[redacted] Bearer [redacted]"
    )
