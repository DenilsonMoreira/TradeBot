from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_audit_service, get_operator_session
from app.schemas.audit import AuditEventResponse
from app.services.audit_service import AuditService


router = APIRouter(prefix="/audit-events", tags=["audit"])


@router.get("", response_model=list[AuditEventResponse], dependencies=[Depends(get_operator_session)])
def list_audit_events(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: AuditService = Depends(get_audit_service),
):
    return service.list(limit, offset)
