from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_audit_service,
    get_notification_service,
    get_operator_session,
    require_operator_csrf,
)
from app.config import settings
from app.core.security import OperatorSession
from app.database import get_db
from app.schemas.soak import SoakStartRequest, SoakStatusResponse
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.services.soak_service import TestnetSoakService


router = APIRouter(prefix="/testnet/soak", tags=["testnet-soak"])


@router.get(
    "",
    response_model=SoakStatusResponse,
    dependencies=[Depends(get_operator_session)],
)
def get_soak_status(db: Session = Depends(get_db)):
    return TestnetSoakService(db).status()


@router.post("/start", response_model=SoakStatusResponse, status_code=201)
def start_soak_campaign(
    payload: SoakStartRequest,
    db: Session = Depends(get_db),
    session: OperatorSession = Depends(require_operator_csrf),
    audit: AuditService = Depends(get_audit_service),
    notifications: NotificationService = Depends(get_notification_service),
):
    if not settings.binance_testnet:
        raise HTTPException(400, "A campanha só pode ser iniciada na Binance Testnet.")
    if payload.confirmation != "INICIAR TESTE R$ 500":
        raise HTTPException(
            400,
            'Confirmação inválida. Envie "INICIAR TESTE R$ 500".',
        )
    service = TestnetSoakService(db)
    try:
        campaign = service.start(duration_hours=payload.duration_hours)
        db.commit()
        db.refresh(campaign)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    audit.record(
        session.email,
        "TESTNET_SOAK_STARTED",
        "testnet_soak_campaign",
        resource_id=str(campaign.id),
        details={
            "budget_brl": campaign.budget_brl,
            "budget_quote": campaign.budget_quote,
            "duration_hours": campaign.duration_hours,
            "automatic_entries_changed": False,
        },
    )
    notifications.create(
        session.email,
        "INFO",
        "TESTNET_SOAK_STARTED",
        "Teste contínuo de R$ 500 iniciado",
        "A campanha apenas observa o ambiente Testnet e não habilita entradas automáticas.",
        resource_id=str(campaign.id),
    )
    return service.status()

