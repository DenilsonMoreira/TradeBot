from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, notification: Notification) -> Notification:
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def list(self, recipient: str, *, unread_only: bool, limit: int) -> list[Notification]:
        statement = select(Notification).where(Notification.recipient == recipient)
        if unread_only:
            statement = statement.where(Notification.read_at.is_(None))
        statement = statement.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit)
        return list(self.db.scalars(statement).all())

    def mark_read(self, notification_id: int, recipient: str) -> Notification | None:
        notification = self.db.scalar(select(Notification).where(Notification.id == notification_id, Notification.recipient == recipient))
        if notification is None:
            return None
        if notification.read_at is None:
            notification.read_at = datetime.now(UTC)
            self.db.commit()
            self.db.refresh(notification)
        return notification

    def mark_all_read(self, recipient: str) -> int:
        result = self.db.execute(update(Notification).where(Notification.recipient == recipient, Notification.read_at.is_(None)).values(read_at=datetime.now(UTC)))
        self.db.commit()
        return int(result.rowcount or 0)
