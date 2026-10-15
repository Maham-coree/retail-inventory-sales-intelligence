"""ORM models: Python classes mapped to tables in the 'retail' schema."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

SCHEMA = "retail"


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("category_name", name="categories_category_name_key"),
        {"schema": SCHEMA},
    )

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)


class Supplier(Base):
    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("supplier_name", name="suppliers_supplier_name_key"),
        UniqueConstraint("email", name="suppliers_email_key"),
        CheckConstraint("lead_time_days >= 0", name="suppliers_lead_time_days_check"),
        {"schema": SCHEMA},
    )

    supplier_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier_name: Mapped[str] = mapped_column(String(120))
    contact_person: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(30))
    city: Mapped[str | None] = mapped_column(String(80))
    lead_time_days: Mapped[int] = mapped_column(Integer, default=3, server_default=text("3"))


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("sku", name="products_sku_key"),
        CheckConstraint("unit_cost >= 0", name="products_unit_cost_check"),
        CheckConstraint("unit_price >= 0", name="products_unit_price_check"),
        CheckConstraint("reorder_level >= 0", name="products_reorder_level_check"),
        CheckConstraint("reorder_quantity > 0", name="products_reorder_quantity_check"),
        CheckConstraint("unit_price >= unit_cost", name="products_price_cost_check"),
        {"schema": SCHEMA},
    )

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(30))
    product_name: Mapped[str] = mapped_column(String(150))
    category_id: Mapped[int] = mapped_column(
        ForeignKey(
            f"{SCHEMA}.categories.category_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        )
    )
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey(
            f"{SCHEMA}.suppliers.supplier_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        )
    )
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reorder_level: Mapped[int] = mapped_column(Integer, default=10, server_default=text("10"))
    reorder_quantity: Mapped[int] = mapped_column(Integer, default=50, server_default=text("50"))
    barcode: Mapped[str | None] = mapped_column(String(50), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    category: Mapped[Category] = relationship()
    supplier: Mapped[Supplier] = relationship()


class Store(Base):
    __tablename__ = "stores"
    __table_args__ = (
        UniqueConstraint("store_name", name="stores_store_name_key"),
        {"schema": SCHEMA},
    )

    store_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    store_name: Mapped[str] = mapped_column(String(100), unique=True)
    city: Mapped[str] = mapped_column(String(80))
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(30))


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (
        CheckConstraint("quantity_on_hand >= 0", name="inventory_quantity_on_hand_check"),
        {"schema": SCHEMA},
    )

    store_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.stores.store_id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.products.product_id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint(
            "role IN ('Manager','Cashier','Stock Clerk')",
            name="employees_role_check",
        ),
        UniqueConstraint("email", name="employees_email_key"),
        {"schema": SCHEMA},
    )

    employee_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    store_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.stores.store_id", onupdate="CASCADE", ondelete="RESTRICT")
    )
    full_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(120), unique=True)
    hire_date: Mapped[date] = mapped_column(Date, server_default=func.current_date())


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("email", name="customers_email_key"),
        {"schema": SCHEMA},
    )

    customer_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(120), unique=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    city: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint(
            "payment_method IN ('Cash','Card','Online')",
            name="sales_payment_method_check",
        ),
        CheckConstraint("total_amount >= 0", name="sales_total_amount_check"),
        {"schema": SCHEMA},
    )

    sale_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    store_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.stores.store_id", onupdate="CASCADE", ondelete="RESTRICT")
    )
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            f"{SCHEMA}.customers.customer_id",
            onupdate="CASCADE",
            ondelete="SET NULL",
        )
    )
    employee_id: Mapped[int] = mapped_column(
        ForeignKey(
            f"{SCHEMA}.employees.employee_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        )
    )
    sale_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    payment_method: Mapped[str] = mapped_column(
        String(20), default="Cash", server_default=text("'Cash'")
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=0, server_default=text("0")
    )


class SaleItem(Base):
    __tablename__ = "sale_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="sale_items_quantity_check"),
        CheckConstraint("unit_price >= 0", name="sale_items_unit_price_check"),
        CheckConstraint("discount >= 0", name="sale_items_discount_check"),
        {"schema": SCHEMA},
    )

    sale_item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sale_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.sales.sale_id", onupdate="CASCADE", ondelete="CASCADE")
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey(
            f"{SCHEMA}.products.product_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        )
    )
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, server_default=text("0"))
    line_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        Computed("quantity * unit_price - discount", persisted=True),
    )


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('Draft','Ordered','Received','Cancelled')",
            name="purchase_orders_status_check",
        ),
        CheckConstraint(
            "expected_date IS NULL OR expected_date >= order_date",
            name="purchase_orders_expected_date_check",
        ),
        {"schema": SCHEMA},
    )

    po_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey(
            f"{SCHEMA}.suppliers.supplier_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        )
    )
    store_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.stores.store_id", onupdate="CASCADE", ondelete="RESTRICT")
    )
    order_date: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    expected_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(15), default="Draft", server_default=text("'Draft'"))


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    __table_args__ = (
        UniqueConstraint("po_id", "product_id", name="purchase_order_items_po_id_product_id_key"),
        CheckConstraint("quantity > 0", name="purchase_order_items_quantity_check"),
        CheckConstraint("unit_cost >= 0", name="purchase_order_items_unit_cost_check"),
        CheckConstraint("received_qty >= 0", name="purchase_order_items_received_qty_check"),
        CheckConstraint(
            "received_qty <= quantity", name="purchase_order_items_received_limit_check"
        ),
        {"schema": SCHEMA},
    )

    po_item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    po_id: Mapped[int] = mapped_column(
        ForeignKey(
            f"{SCHEMA}.purchase_orders.po_id",
            onupdate="CASCADE",
            ondelete="CASCADE",
        )
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey(
            f"{SCHEMA}.products.product_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        )
    )
    quantity: Mapped[int] = mapped_column(Integer)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    received_qty: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint(
            "movement_type IN ('SALE','PURCHASE','ADJUSTMENT','RETURN')",
            name="stock_movements_movement_type_check",
        ),
        CheckConstraint("quantity <> 0", name="stock_movements_quantity_check"),
        {"schema": SCHEMA},
    )

    movement_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    store_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.stores.store_id", onupdate="CASCADE", ondelete="CASCADE")
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.products.product_id", onupdate="CASCADE", ondelete="CASCADE")
    )
    movement_type: Mapped[str] = mapped_column(String(15))
    quantity: Mapped[int] = mapped_column(Integer)
    reference: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
