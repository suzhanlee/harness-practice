from __future__ import annotations
from typing import Dict, List
from uuid import UUID

from kiosk.domain.repositories.notification_repository import Notification, NotificationRepository


class InMemoryNotificationRepository(NotificationRepository):
    def __init__(self):
        self._notifications: Dict[UUID, Notification] = {}

    def save(self, notification: Notification) -> None:
        self._notifications[notification.id] = notification

    def find_by_order_id(self, order_id_value: str) -> List[Notification]:
        return [n for n in self._notifications.values() if n.order_id_value == order_id_value]

    def find_all(self) -> List[Notification]:
        return list(self._notifications.values())
