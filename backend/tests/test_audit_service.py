from unittest.mock import Mock

from app.services.audit_service import AuditService


def test_record_builds_sanitized_audit_event() -> None:
    repository = Mock()
    repository.add.side_effect = lambda event: event
    service = AuditService(repository)

    event = service.record(
        "operator@example.com",
        "BOT_MODE_CHANGED",
        "bot",
        resource_id="1",
        details={"mode": "MONITOR"},
    )

    assert event.actor == "operator@example.com"
    assert event.details == {"mode": "MONITOR"}
    repository.add.assert_called_once_with(event)
