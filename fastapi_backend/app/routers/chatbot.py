"""Authenticated HTTP endpoints for the retail assistant."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import schemas
from ..config import settings
from ..database import get_db
from ..deps import get_current_user, require_roles
from ..repositories import chatbot as chatbot_repository
from ..services.chatbot_service import get_suggestions, handle_message

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


def _require_enabled() -> None:
    if not settings.chatbot_enabled:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The retail assistant is disabled by the administrator",
        )


@router.post(
    "/message",
    response_model=schemas.ChatbotMessageResponse,
    summary="Send a message to the retail assistant",
)
def post_message(
    data: schemas.ChatbotMessageRequest,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_enabled()
    message = data.message.strip()
    if not message or len(message) > settings.chatbot_max_message_length:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Message must contain 1 to {settings.chatbot_max_message_length} characters",
        )
    response = handle_message(db, user, data.model_copy(update={"message": message}))
    db.commit()
    return response


@router.get("/suggestions", summary="Get starter questions for the current role")
def suggestions(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, list[str]]:
    _require_enabled()
    return {"suggestions": get_suggestions(str(user["role"]))}


@router.post("/feedback", summary="Rate one of your assistant replies")
def feedback(
    data: schemas.ChatbotFeedbackRequest,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    _require_enabled()
    updated = chatbot_repository.update_feedback(
        db, int(user["user_id"]), data.message_id, data.helpful
    )
    if not updated:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat message not found")
    db.commit()
    return {"message": "Feedback recorded"}


@router.get("/history", summary="Get the current user's recent assistant messages")
def history(
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_enabled()
    return {
        "messages": chatbot_repository.get_history(db, int(user["user_id"]), limit)
    }


@router.get("/stats", summary="Get assistant usage statistics (admin only)")
def stats(
    db: Session = Depends(get_db),
    _: dict[str, Any] = Depends(require_roles("admin")),
) -> dict[str, Any]:
    _require_enabled()
    return chatbot_repository.get_chatbot_stats(db)
