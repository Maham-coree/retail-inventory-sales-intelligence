"""Pydantic schemas: validate what comes in and shape what goes out."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProductBase(BaseModel):
    sku: str = Field(min_length=2, max_length=30)
    product_name: str = Field(min_length=2, max_length=150)
    category_id: int
    supplier_id: int
    unit_cost: Decimal = Field(ge=0)
    unit_price: Decimal = Field(ge=0)
    reorder_level: int = Field(default=10, ge=0)
    reorder_quantity: int = Field(default=50, gt=0)
    is_active: bool = True
    barcode: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def price_not_below_cost(self):
        if self.unit_price < self.unit_cost:
            raise ValueError("unit_price must be greater than or equal to unit_cost")
        return self


class ProductCreate(ProductBase):
    """Request body for POST and PUT."""


class ProductUpdate(BaseModel):
    """Request body for PATCH: every field is optional."""

    sku: str | None = Field(default=None, min_length=2, max_length=30)
    product_name: str | None = Field(default=None, min_length=2, max_length=150)
    category_id: int | None = None
    supplier_id: int | None = None
    unit_cost: Decimal | None = Field(default=None, ge=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    reorder_level: int | None = Field(default=None, ge=0)
    reorder_quantity: int | None = Field(default=None, gt=0)
    is_active: bool | None = None
    barcode: str | None = Field(default=None, max_length=50)


class ProductOut(ProductBase):
    """Response body."""

    product_id: int
    model_config = ConfigDict(from_attributes=True)


class CategoryIn(BaseModel):
    category_name: str = Field(min_length=1, max_length=80)
    description: str | None = None


class SupplierIn(BaseModel):
    supplier_name: str = Field(min_length=1, max_length=120)
    contact_person: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    city: str | None = Field(default=None, max_length=80)
    lead_time_days: int = Field(default=3, ge=0)


class StoreIn(BaseModel):
    store_name: str = Field(min_length=1, max_length=100)
    city: str = Field(min_length=1, max_length=80)
    address: str | None = None
    phone: str | None = Field(default=None, max_length=30)


class CustomerIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    city: str | None = Field(default=None, max_length=80)


class EmployeeIn(BaseModel):
    store_id: int
    full_name: str = Field(min_length=1, max_length=100)
    role: str = Field(pattern="^(Manager|Cashier|Stock Clerk)$")
    email: str | None = Field(default=None, max_length=120)


class SaleLineIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    discount: Decimal = Field(default=Decimal("0"), ge=0)


class SaleCreate(BaseModel):
    store_id: int
    customer_id: int | None = None
    employee_id: int | None = None
    payment_method: str = Field(default="Cash", pattern="^(Cash|Card|Online)$")
    items: list[SaleLineIn] = Field(min_length=1)


class InventoryAdjust(BaseModel):
    store_id: int
    product_id: int
    delta: int
    reason: str = Field(min_length=1, max_length=50)


class PurchaseOrderLineIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    store_id: int
    expected_date: date | None = None
    items: list[PurchaseOrderLineIn] = Field(min_length=1)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=72)
    role: str = Field(pattern="^(admin|manager|cashier)$")
    employee_id: int | None = None


class PasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=72)
