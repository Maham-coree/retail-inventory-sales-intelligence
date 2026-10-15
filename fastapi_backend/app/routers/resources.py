"""Product and business-directory CRUD endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles
from ..repositories.queries import fetch_rows

router = APIRouter(tags=["business data"])


def db_error(exc: IntegrityError) -> HTTPException:
    original = exc.orig
    code = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    if code == "23505":
        return HTTPException(409, "A record with that unique value already exists")
    if code == "23503":
        return HTTPException(409, "Related records prevent this change")
    if code == "23514":
        message = str(original).lower()
        if "inventory" in message or "stock" in message or "quantity" in message:
            return HTTPException(409, "Insufficient stock for this operation")
        return HTTPException(400, "A database validation rule failed")
    return HTTPException(400, "Database constraint rejected the operation")


@router.get("/products", summary="List or search products")
def list_products(
    search: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    sort: str = "product_id",
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(get_current_user),
) -> Any:
    del user
    allowed_sort = {
        "product_id",
        "sku",
        "product_name",
        "unit_price",
        "unit_cost",
    }
    if sort not in allowed_sort:
        raise HTTPException(422, "Unsupported product sort field")
    query = select(models.Product).order_by(getattr(models.Product, sort))
    if search:
        pattern = f"%{search}%"
        query = query.where(
            models.Product.product_name.ilike(pattern) | models.Product.sku.ilike(pattern)
        )
    if page is None:
        return [
            schemas.ProductOut.model_validate(product).model_dump()
            for product in db.scalars(query).all()
        ]
    if search:
        total = db.execute(
            text(
                "SELECT count(*) FROM retail.products "
                "WHERE product_name ILIKE :pattern OR sku ILIKE :pattern"
            ),
            {"pattern": f"%{search}%"},
        ).scalar_one()
    else:
        total = db.execute(text("SELECT count(*) FROM retail.products")).scalar_one()
    items = [
        schemas.ProductOut.model_validate(product).model_dump()
        for product in db.scalars(
            query.offset((page - 1) * page_size).limit(page_size)
        ).all()
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get(
    "/products/{product_id}",
    response_model=schemas.ProductOut,
    summary="Get one product",
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(get_current_user),
) -> Any:
    product = db.get(models.Product, product_id)
    if product is None:
        raise HTTPException(404, "Product not found")
    return product


@router.post(
    "/products",
    response_model=schemas.ProductOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
)
def create_product(
    data: schemas.ProductCreate,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_roles("admin", "manager")),
) -> models.Product:
    product = models.Product(**data.model_dump())
    db.add(product)
    try:
        db.commit()
        db.refresh(product)
    except IntegrityError as exc:
        db.rollback()
        raise db_error(exc) from exc
    return product


@router.put(
    "/products/{product_id}", response_model=schemas.ProductOut, summary="Replace a product"
)
def replace_product(
    product_id: int,
    data: schemas.ProductCreate,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_roles("admin", "manager")),
) -> models.Product:
    product = db.get(models.Product, product_id)
    if product is None:
        raise HTTPException(404, "Product not found")
    for field, value in data.model_dump().items():
        setattr(product, field, value)
    try:
        db.commit()
        db.refresh(product)
    except IntegrityError as exc:
        db.rollback()
        raise db_error(exc) from exc
    return product


@router.patch(
    "/products/{product_id}", response_model=schemas.ProductOut, summary="Update product fields"
)
def update_product(
    product_id: int,
    data: schemas.ProductUpdate,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_roles("admin", "manager")),
) -> models.Product:
    product = db.get(models.Product, product_id)
    if product is None:
        raise HTTPException(404, "Product not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    try:
        db.commit()
        db.refresh(product)
    except IntegrityError as exc:
        db.rollback()
        raise db_error(exc) from exc
    return product


@router.delete("/products/{product_id}", status_code=204, summary="Delete a product")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_roles("admin")),
) -> None:
    product = db.get(models.Product, product_id)
    if product is None:
        raise HTTPException(404, "Product not found")
    db.delete(product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise db_error(exc) from exc


def register_resource(
    path: str,
    table: str,
    id_column: str,
    schema: type,
    read_roles: tuple[str, ...],
    write_roles: tuple[str, ...],
    delete_roles: tuple[str, ...] = ("admin",),
) -> None:
    columns = tuple(schema.model_fields)

    def list_items(
        search: str | None = None,
        page: int | None = Query(default=None, ge=1),
        page_size: int = Query(default=20, ge=1, le=200),
        sort: str = id_column,
        db: Session = Depends(get_db),
        _: dict[str, object] = Depends(require_roles(*read_roles)),
    ) -> Any:
        allowed_sort = {id_column, *columns}
        if sort not in allowed_sort:
            raise HTTPException(422, "Unsupported sort field")
        where = ""
        params: dict[str, Any] = {}
        if search:
            text_columns = [name for name in columns if name not in {"lead_time_days", "store_id"}]
            where = " WHERE " + " OR ".join(
                f"CAST({column} AS text) ILIKE :search" for column in text_columns
            )
            params["search"] = f"%{search}%"
        query = (
            f"SELECT {id_column}, {', '.join(columns)} FROM retail.{table}"
            + where
            + f" ORDER BY {sort}"
        )
        if page is None:
            return fetch_rows(db, query, params)
        total = db.execute(
            text(f"SELECT count(*) FROM retail.{table}" + where), params
        ).scalar_one()
        params.update({"limit": page_size, "offset": (page - 1) * page_size})
        items = fetch_rows(db, query + " LIMIT :limit OFFSET :offset", params)
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def get_item(
        item_id: int,
        db: Session = Depends(get_db),
        _: dict[str, object] = Depends(require_roles(*read_roles)),
    ) -> dict[str, Any]:
        row = (
            db.execute(
                text(
                    f"SELECT {id_column}, {', '.join(columns)} FROM retail.{table} "
                    f"WHERE {id_column} = :item_id"
                ),
                {"item_id": item_id},
            )
            .mappings()
            .first()
        )
        if row is None:
            raise HTTPException(404, f"{path.rstrip('/').title()} not found")
        return dict(row)

    def create_item(
        data: Any,
        db: Session = Depends(get_db),
        _: dict[str, object] = Depends(require_roles(*write_roles)),
    ) -> dict[str, Any]:
        values = data.model_dump()
        names = ", ".join(values)
        binds = ", ".join(f":{name}" for name in values)
        try:
            row = (
                db.execute(
                    text(
                        f"INSERT INTO retail.{table} ({names}) VALUES ({binds}) "
                        f"RETURNING {id_column}, {', '.join(columns)}"
                    ),
                    values,
                )
                .mappings()
                .one()
            )
            db.commit()
            return dict(row)
        except IntegrityError as exc:
            db.rollback()
            raise db_error(exc) from exc

    def update_item(
        item_id: int,
        data: Any,
        db: Session = Depends(get_db),
        _: dict[str, object] = Depends(require_roles(*write_roles)),
    ) -> dict[str, Any]:
        values = data.model_dump()
        setters = ", ".join(f"{name} = :{name}" for name in values)
        values["item_id"] = item_id
        try:
            row = (
                db.execute(
                    text(
                        f"UPDATE retail.{table} SET {setters} "
                        f"WHERE {id_column} = :item_id "
                        f"RETURNING {id_column}, {', '.join(columns)}"
                    ),
                    values,
                )
                .mappings()
                .first()
            )
            if row is None:
                db.rollback()
                raise HTTPException(404, f"{path.rstrip('/').title()} not found")
            db.commit()
            return dict(row)
        except IntegrityError as exc:
            db.rollback()
            raise db_error(exc) from exc

    def delete_item(
        item_id: int,
        db: Session = Depends(get_db),
        _: dict[str, object] = Depends(require_roles(*delete_roles)),
    ) -> None:
        try:
            result = db.execute(
                text(f"DELETE FROM retail.{table} WHERE {id_column} = :item_id"),
                {"item_id": item_id},
            )
            if result.rowcount == 0:
                db.rollback()
                raise HTTPException(404, f"{path.rstrip('/').title()} not found")
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise db_error(exc) from exc

    list_items.__name__ = f"list_{table}"
    get_item.__name__ = f"get_{table.rstrip('s')}"
    create_item.__name__ = f"create_{table.rstrip('s')}"
    update_item.__name__ = f"update_{table.rstrip('s')}"
    delete_item.__name__ = f"delete_{table.rstrip('s')}"
    create_item.__annotations__["data"] = schema
    update_item.__annotations__["data"] = schema
    router.add_api_route(path, list_items, methods=["GET"], summary=f"List {table}")
    router.add_api_route(
        f"{path}/{{item_id}}", get_item, methods=["GET"], summary=f"Get {table[:-1]}"
    )
    router.add_api_route(
        path, create_item, methods=["POST"], status_code=201, summary=f"Create {table[:-1]}"
    )
    router.add_api_route(
        f"{path}/{{item_id}}", update_item, methods=["PUT"], summary=f"Update {table[:-1]}"
    )
    router.add_api_route(
        f"{path}/{{item_id}}",
        delete_item,
        methods=["DELETE"],
        status_code=204,
        summary=f"Delete {table[:-1]}",
    )


register_resource(
    "/categories",
    "categories",
    "category_id",
    schemas.CategoryIn,
    ("admin", "manager", "cashier"),
    ("admin", "manager"),
)
register_resource(
    "/suppliers",
    "suppliers",
    "supplier_id",
    schemas.SupplierIn,
    ("admin", "manager", "cashier"),
    ("admin", "manager"),
)
register_resource(
    "/stores",
    "stores",
    "store_id",
    schemas.StoreIn,
    ("admin", "manager", "cashier"),
    ("admin", "manager"),
)
register_resource(
    "/customers",
    "customers",
    "customer_id",
    schemas.CustomerIn,
    ("admin", "manager", "cashier"),
    ("admin", "manager", "cashier"),
)
register_resource(
    "/employees",
    "employees",
    "employee_id",
    schemas.EmployeeIn,
    ("admin", "manager"),
    ("admin", "manager"),
    ("admin",),
)
