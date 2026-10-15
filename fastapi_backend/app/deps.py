"""Authentication and role dependencies shared by API routers."""

from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import get_db
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> dict[str, object]:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
        if not isinstance(username, str):
            raise unauthorized
    except (jwt.PyJWTError, ValueError):
        raise unauthorized from None
    user = (
        db.execute(
            text(
                "SELECT user_id, username, role, employee_id, is_active "
                "FROM retail.app_users WHERE username = :username"
            ),
            {"username": username},
        )
        .mappings()
        .first()
    )
    if user is None or not user["is_active"]:
        raise unauthorized
    return dict(user)


def require_roles(*roles: str) -> Callable:
    def dependency(
        user: dict[str, object] = Depends(get_current_user),
    ) -> dict[str, object]:
        if user["role"] not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user

    return dependency
