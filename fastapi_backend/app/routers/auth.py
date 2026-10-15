"""Login, current-user, and administrative user-management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import get_current_user, require_roles
from ..repositories.queries import fetch_rows
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(tags=["authentication"])


@router.post("/auth/login", summary="Create a bearer access token")
def login(
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> dict[str, object]:
    user = (
        db.execute(
            text(
                "SELECT user_id, username, password_hash, role, employee_id, is_active "
                "FROM retail.app_users WHERE username = :username"
            ),
            {"username": form.username},
        )
        .mappings()
        .first()
    )
    if (
        user is None
        or not user["is_active"]
        or not verify_password(form.password, user["password_hash"])
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "access_token": create_access_token(user["username"], user["role"]),
        "token_type": "bearer",
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "role": user["role"],
            "employee_id": user["employee_id"],
        },
    }


@router.get("/auth/me", summary="Return the authenticated user")
def me(user: dict[str, object] = Depends(get_current_user)) -> dict[str, object]:
    return user


@router.get("/users", summary="List application users")
def list_users(
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_roles("admin")),
) -> list[dict[str, object]]:
    return fetch_rows(
        db,
        "SELECT user_id, public_id, username, role, employee_id, is_active, created_at "
        "FROM retail.app_users ORDER BY user_id",
    )


@router.post("/users", status_code=status.HTTP_201_CREATED, summary="Create an application user")
def create_user(
    data: schemas.UserCreate,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_roles("admin")),
) -> dict[str, object]:
    try:
        row = (
            db.execute(
                text(
                    "INSERT INTO retail.app_users (username, password_hash, role, employee_id) "
                    "VALUES (:username, :password_hash, :role, :employee_id) "
                    "RETURNING user_id, username, role, employee_id, is_active, created_at"
                ),
                {
                    "username": data.username,
                    "password_hash": hash_password(data.password),
                    "role": data.role,
                    "employee_id": data.employee_id,
                },
            )
            .mappings()
            .one()
        )
        db.commit()
        return dict(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Username or employee is already in use") from exc


@router.post("/users/{user_id}/deactivate", summary="Deactivate an application user")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_roles("admin")),
) -> dict[str, str]:
    result = db.execute(
        text("UPDATE retail.app_users SET is_active = false WHERE user_id = :user_id"),
        {"user_id": user_id},
    )
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(404, "User not found")
    db.commit()
    return {"message": "User deactivated"}


@router.post("/users/{user_id}/reset-password", summary="Reset a user's password")
def reset_password(
    user_id: int,
    data: schemas.PasswordReset,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_roles("admin")),
) -> dict[str, str]:
    result = db.execute(
        text("UPDATE retail.app_users SET password_hash = :password_hash WHERE user_id = :user_id"),
        {"password_hash": hash_password(data.password), "user_id": user_id},
    )
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(404, "User not found")
    db.commit()
    return {"message": "Password reset"}
