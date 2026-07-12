from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository


class NotificationService:
    def __init__(self, repository: NotificationRepository):
        self.repository = repository

    def create(self, recipient: str, severity: str, category: str, title: str, message: str, *, resource_id: str | None = None) -> Notification:
        return self.repository.add(Notification(recipient=recipient, severity=severity, category=category, title=title, message=message, resource_id=resource_id))

    def list(self, recipient: str, *, unread_only: bool = False, limit: int = 50) -> list[Notification]:
        return self.repository.list(recipient, unread_only=unread_only, limit=limit)

    def mark_read(self, notification_id: int, recipient: str) -> Notification:
        notification = self.repository.mark_read(notification_id, recipient)
        if notification is None:
            raise ValueError("Notificação não encontrada.")
        return notification

    def mark_all_read(self, recipient: str) -> int:
        return self.repository.mark_all_read(recipient)
