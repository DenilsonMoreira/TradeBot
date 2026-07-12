from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_notification_service, get_operator_session, require_operator_csrf
from app.core.security import OperatorSession
from app.schemas.notification import MarkAllReadResponse, NotificationResponse
from app.services.notification_service import NotificationService


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
def list_notifications(unread_only: bool = False, limit: int = Query(default=50, ge=1, le=200), session: OperatorSession = Depends(get_operator_session), service: NotificationService = Depends(get_notification_service)):
    return service.list(session.email, unread_only=unread_only, limit=limit)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(notification_id: int, session: OperatorSession = Depends(require_operator_csrf), service: NotificationService = Depends(get_notification_service)):
    try:
        return service.mark_read(notification_id, session.email)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/read-all", response_model=MarkAllReadResponse)
def mark_all_notifications_read(session: OperatorSession = Depends(require_operator_csrf), service: NotificationService = Depends(get_notification_service)):
    return MarkAllReadResponse(updated=service.mark_all_read(session.email))
