from datetime import datetime

from pydantic import BaseModel


class ReadinessCheckResponse(BaseModel):
    id: str
    label: str
    status: str
    detail: str
    gates: list[str]


class ReadinessSummaryResponse(BaseModel):
    passed: int
    pending: int
    failed: int
    total: int


class ReadinessReportResponse(BaseModel):
    generated_at: datetime
    environment: str
    local_stack_ready: bool
    server_release_ready: bool
    automatic_trading_ready: bool
    summary: ReadinessSummaryResponse
    checks: list[ReadinessCheckResponse]

