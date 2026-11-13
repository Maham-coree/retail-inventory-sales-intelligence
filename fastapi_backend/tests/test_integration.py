"""Local PostgreSQL integration coverage; skipped when the server is unreachable."""

import uuid
from collections.abc import Generator

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal


def database_is_available() -> bool:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False


@pytest.fixture(autouse=True, scope="module")
def require_postgres() -> None:
    if not database_is_available():
        pytest.skip("Configured PostgreSQL database is unreachable")


@pytest.fixture()
def chatbot_message_cleanup() -> Generator[list[int]]:
    message_ids: list[int] = []
    yield message_ids
    with SessionLocal.begin() as db:
        for message_id in message_ids:
            db.execute(
                text("DELETE FROM retail.chat_messages WHERE message_id = :message_id"),
                {"message_id": message_id},
            )


pytestmark = pytest.mark.integration


def token(client, username: str, password: str) -> str:
    response = client.post("/auth/login", data={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_login_for_each_role(client) -> None:
    for username, password, role in (
        ("admin", "Admin@123", "admin"),
        ("manager", "Manager@123", "manager"),
        ("cashier", "Cashier@123", "cashier"),
    ):
        result = client.post("/auth/login", data={"username": username, "password": password})
        assert result.status_code == 200
        assert result.json()["user"]["role"] == role


def test_product_create_read_update_delete_and_duplicate(client) -> None:
    admin = token(client, "admin", "Admin@123")
    headers = {"Authorization": f"Bearer {admin}"}
    with SessionLocal() as db:
        category_id = db.execute(
            text("SELECT category_id FROM retail.categories LIMIT 1")
        ).scalar_one()
        supplier_id = db.execute(
            text("SELECT supplier_id FROM retail.suppliers LIMIT 1")
        ).scalar_one()
    sku = f"TEST-{uuid.uuid4().hex[:10]}"
    payload = {
        "sku": sku,
        "product_name": "Integration product",
        "category_id": category_id,
        "supplier_id": supplier_id,
        "unit_cost": 10,
        "unit_price": 15,
    }
    created = client.post("/products", headers=headers, json=payload)
    assert created.status_code == 201
    product_id = created.json()["product_id"]
    try:
        assert client.get(f"/products/{product_id}", headers=headers).status_code == 200
        changed = client.patch(f"/products/{product_id}", headers=headers, json={"unit_price": 16})
        assert changed.status_code == 200
        assert float(changed.json()["unit_price"]) == 16
        duplicate = client.post("/products", headers=headers, json=payload)
        assert duplicate.status_code == 409
    finally:
        client.delete(f"/products/{product_id}", headers=headers)
    assert client.get(f"/products/{product_id}", headers=headers).status_code == 404


def test_authentication_and_cashier_delete_forbidden(client) -> None:
    cashier = token(client, "cashier", "Cashier@123")
    with SessionLocal() as db:
        product_id = db.execute(text("SELECT product_id FROM retail.products LIMIT 1")).scalar_one()
    assert (
        client.get("/products", headers={"Authorization": f"Bearer {cashier}"}).status_code == 200
    )
    assert (
        client.delete(
            f"/products/{product_id}", headers={"Authorization": f"Bearer {cashier}"}
        ).status_code
        == 403
    )
    assert client.get("/products").status_code == 401


def test_sale_reduces_stock_and_insufficient_stock_is_rejected(client) -> None:
    admin = token(client, "admin", "Admin@123")
    headers = {"Authorization": f"Bearer {admin}"}
    with SessionLocal() as db:
        stocked = (
            db.execute(
                text(
                    "SELECT store_id, product_id, quantity_on_hand FROM retail.inventory "
                    "WHERE quantity_on_hand > 0 ORDER BY store_id, product_id LIMIT 1"
                )
            )
            .mappings()
            .one()
        )
        employee_id = db.execute(
            text("SELECT employee_id FROM retail.employees LIMIT 1")
        ).scalar_one()
    before = stocked["quantity_on_hand"]
    payload = {
        "store_id": stocked["store_id"],
        "employee_id": employee_id,
        "payment_method": "Cash",
        "items": [{"product_id": stocked["product_id"], "quantity": 1}],
    }
    response = client.post("/sales", headers=headers, json=payload)
    assert response.status_code == 201
    sale_id = response.json()["sale"]["sale_id"]
    with SessionLocal() as db:
        after = db.execute(
            text(
                "SELECT quantity_on_hand FROM retail.inventory "
                "WHERE store_id=:store AND product_id=:product"
            ),
            {"store": stocked["store_id"], "product": stocked["product_id"]},
        ).scalar_one()
    assert after == before - 1
    too_many = {
        **payload,
        "items": [{"product_id": stocked["product_id"], "quantity": after + 1000}],
    }
    assert client.post("/sales", headers=headers, json=too_many).status_code == 409
    with SessionLocal.begin() as db:
        db.execute(
            text("DELETE FROM retail.stock_movements WHERE reference=:reference"),
            {"reference": f"SALE-{sale_id}"},
        )
        db.execute(
            text(
                "UPDATE retail.inventory SET quantity_on_hand=:qty "
                "WHERE store_id=:store AND product_id=:product"
            ),
            {"qty": before, "store": stocked["store_id"], "product": stocked["product_id"]},
        )
        db.execute(text("DELETE FROM retail.sales WHERE sale_id=:id"), {"id": sale_id})


def test_chatbot_requires_authentication_and_denies_cashier_sales_data(
    client, chatbot_message_cleanup
) -> None:
    assert client.post("/chatbot/message", json={"message": "sales today"}).status_code == 401
    cashier = token(client, "cashier", "Cashier@123")
    response = client.post(
        "/chatbot/message",
        headers={"Authorization": f"Bearer {cashier}"},
        json={"message": "sales today"},
    )
    assert response.status_code == 200
    chatbot_message_cleanup.append(response.json()["message_id"])
    assert response.json()["intent"] == "sales_summary"
    assert "cannot" in response.json()["reply"].lower()


def test_chatbot_manager_can_get_sales_summary(client, chatbot_message_cleanup) -> None:
    manager = token(client, "manager", "Manager@123")
    response = client.post(
        "/chatbot/message",
        headers={"Authorization": f"Bearer {manager}"},
        json={"message": "sales today"},
    )
    assert response.status_code == 200
    chatbot_message_cleanup.append(response.json()["message_id"])
    assert response.json()["intent"] == "sales_summary"
    assert response.json()["data"]["type"] == "table"
    assert response.json()["data"]["rows"] is not None


def test_chatbot_product_availability_matches_inventory(
    client, chatbot_message_cleanup
) -> None:
    admin = token(client, "admin", "Admin@123")
    headers = {"Authorization": f"Bearer {admin}"}
    products = client.get("/products", headers=headers).json()
    product = products[0]
    inventory = client.get(
        f"/inventory?product_id={product['product_id']}", headers=headers
    ).json()
    response = client.post(
        "/chatbot/message",
        headers=headers,
        json={"message": f"stock of {product['product_name']}"},
    )
    assert response.status_code == 200
    chatbot_message_cleanup.append(response.json()["message_id"])
    rows = response.json()["data"]["rows"]
    assert rows
    expected = {row["store_name"]: row["quantity_on_hand"] for row in inventory}
    actual = {row["store_name"]: row["quantity_on_hand"] for row in rows}
    assert actual == expected


def test_chatbot_history_and_feedback_are_user_owned(
    client, chatbot_message_cleanup
) -> None:
    cashier = token(client, "cashier", "Cashier@123")
    admin = token(client, "admin", "Admin@123")
    cashier_headers = {"Authorization": f"Bearer {cashier}"}
    admin_headers = {"Authorization": f"Bearer {admin}"}
    cashier_message = client.post(
        "/chatbot/message", headers=cashier_headers, json={"message": "hello"}
    ).json()
    chatbot_message_cleanup.append(cashier_message["message_id"])
    admin_message = client.post(
        "/chatbot/message", headers=admin_headers, json={"message": "hello"}
    ).json()
    chatbot_message_cleanup.append(admin_message["message_id"])
    admin_history = client.get("/chatbot/history", headers=admin_headers)
    assert admin_history.status_code == 200
    assert cashier_message["message_id"] not in {
        item["message_id"] for item in admin_history.json()["messages"]
    }
    assert client.post(
        "/chatbot/feedback",
        headers=admin_headers,
        json={"message_id": cashier_message["message_id"], "helpful": True},
    ).status_code == 404
    assert client.post(
        "/chatbot/feedback",
        headers=cashier_headers,
        json={"message_id": cashier_message["message_id"], "helpful": True},
    ).status_code == 200


def test_chatbot_context_resolves_follow_up_store(client, chatbot_message_cleanup) -> None:
    manager = token(client, "manager", "Manager@123")
    headers = {"Authorization": f"Bearer {manager}"}
    first = client.post(
        "/chatbot/message",
        headers=headers,
        json={"message": "stock of Fresh Milk"},
    )
    assert first.status_code == 200
    chatbot_message_cleanup.append(first.json()["message_id"])
    follow_up = client.post(
        "/chatbot/message",
        headers=headers,
        json={
            "message": "and in the second store?",
            "context": first.json()["context"],
        },
    )
    assert follow_up.status_code == 200
    chatbot_message_cleanup.append(follow_up.json()["message_id"])
    stores = client.get("/stores", headers=headers).json()
    expected_store = sorted(stores, key=lambda row: row["store_id"])[1]["store_name"]
    assert len(follow_up.json()["data"]["rows"]) == 1
    assert follow_up.json()["data"]["rows"][0]["store_name"] == expected_store
