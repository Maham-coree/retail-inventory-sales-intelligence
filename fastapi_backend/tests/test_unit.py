"""Database-independent validation tests."""

import jwt
import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.routers.resources import db_error
from app.schemas import ProductCreate
from app.security import create_access_token, hash_password, verify_password


def valid_product() -> dict[str, object]:
    return {
        "sku": "TEST-UNIT",
        "product_name": "Unit test product",
        "category_id": 1,
        "supplier_id": 1,
        "unit_cost": "10.00",
        "unit_price": "12.00",
    }


def test_product_price_cannot_be_below_cost() -> None:
    data = valid_product()
    data["unit_price"] = "9.99"
    with pytest.raises(ValidationError):
        ProductCreate(**data)


def test_password_hash_and_verification() -> None:
    encoded = hash_password("good-password")
    assert encoded != "good-password"
    assert verify_password("good-password", encoded)
    assert not verify_password("wrong-password", encoded)


def test_jwt_create_and_verify() -> None:
    token = create_access_token("unit-user", "admin")
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    assert payload["sub"] == "unit-user"
    assert payload["role"] == "admin"
    assert payload["exp"] > 0


@pytest.mark.parametrize(
    ("sqlstate", "expected_status"),
    [("23505", 409), ("23503", 409), ("23514", 400), ("99999", 400)],
)
def test_db_error_status_mapping(sqlstate: str, expected_status: int) -> None:
    class OriginalError(Exception):
        pgcode = sqlstate

    error = IntegrityError("statement", {}, OriginalError())
    assert db_error(error).status_code == expected_status
