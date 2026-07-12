from app.models.audit import AuditEvent
from app.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, repository: AuditRepository):
        self.repository = repository

    def record(
        self,
        actor: str,
        action: str,
        resource: str,
        *,
        resource_id: str | None = None,
        details: dict | None = None,
    ) -> AuditEvent:
        return self.repository.add(AuditEvent(
            actor=actor,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=details or {},
        ))

    def list(self, limit: int = 100, offset: int = 0) -> list[AuditEvent]:
        return self.repository.list(limit, offset)
