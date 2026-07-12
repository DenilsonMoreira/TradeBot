from unittest.mock import Mock

import pytest

from app.services.notification_service import NotificationService


def test_create_notification_has_no_secret_payload() -> None:
    repository = Mock()
    repository.add.side_effect = lambda notification: notification
    service = NotificationService(repository)
    notification = service.create("operator@example.com", "CRITICAL", "EMERGENCY_STOP", "Bot parado", "Novas entradas bloqueadas.")
    assert notification.recipient == "operator@example.com"
    assert notification.message == "Novas entradas bloqueadas."
    repository.add.assert_called_once_with(notification)


def test_mark_read_rejects_unknown_notification() -> None:
    repository = Mock()
    repository.mark_read.return_value = None
    with pytest.raises(ValueError, match="não encontrada"):
        NotificationService(repository).mark_read(99, "operator@example.com")
