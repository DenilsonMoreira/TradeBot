from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_operator_session
from app.database import get_db
from app.schemas.readiness import ReadinessReportResponse
from app.services.readiness_service import ReadinessService


router = APIRouter(prefix="/readiness", tags=["readiness"])


@router.get(
    "/report",
    response_model=ReadinessReportResponse,
    dependencies=[Depends(get_operator_session)],
)
def readiness_report(db: Session = Depends(get_db)):
    return ReadinessService(db).report()

