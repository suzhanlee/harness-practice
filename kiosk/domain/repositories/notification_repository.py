from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from uuid import UUID, uuid4


@dataclass
class Notification:
    id: UUID
    order_id_value: str
    message: str
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(cls, order_id_value: str, message: str) -> Notification:
        return cls(id=uuid4(), order_id_value=order_id_value, message=message)


class NotificationRepository(ABC):
    @abstractmethod
    def save(self, notification: Notification) -> None: ...

    @abstractmethod
    def find_by_order_id(self, order_id_value: str) -> List[Notification]: ...

    @abstractmethod
    def find_all(self) -> List[Notification]: ...
