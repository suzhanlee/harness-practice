from __future__ import annotations

from kiosk.domain.events.kitchen_events import TicketReady
from kiosk.domain.repositories.notification_repository import Notification, NotificationRepository


class CustomerNotificationHandler:
    def __init__(self, notification_repo: NotificationRepository):
        self._notification_repo = notification_repo

    def handle(self, event: TicketReady) -> None:
        message = f"번호 {str(event.order_id.value)[:8].upper()} 준비 완료!"
        notification = Notification.create(
            order_id_value=str(event.order_id.value),
            message=message,
        )
        self._notification_repo.save(notification)
