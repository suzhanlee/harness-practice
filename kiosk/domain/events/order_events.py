from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import List
from uuid import UUID

from .base import DomainEvent
from kiosk.domain.models.value_objects import OrderId, Money


@dataclass(frozen=True)
class OrderConfirmed(DomainEvent):
    order_id: OrderId
    items: tuple  # tuple of (name: str, quantity: int, unit_price: Money)
    total_amount: Money

    @classmethod
    def from_order(cls, order_id: OrderId, items: list, total_amount: Money) -> OrderConfirmed:
        from datetime import datetime
        from uuid import uuid4
        return cls(
            event_id=uuid4(),
            occurred_at=datetime.now(),
            order_id=order_id,
            items=tuple(items),
            total_amount=total_amount,
        )
