from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from .base import DomainEvent
from kiosk.domain.models.value_objects import OrderId
from kiosk.domain.models.kitchen_ticket import TicketId


@dataclass(frozen=True)
class KitchenTicketCreated(DomainEvent):
    ticket_id: TicketId
    order_id: OrderId
    items: tuple  # tuple of (name: str, quantity: int)

    @classmethod
    def create(cls, ticket_id: TicketId, order_id: OrderId, items: list) -> KitchenTicketCreated:
        return cls(
            event_id=uuid4(),
            occurred_at=datetime.now(),
            ticket_id=ticket_id,
            order_id=order_id,
            items=tuple(items),
        )


@dataclass(frozen=True)
class ItemPrepared(DomainEvent):
    ticket_id: TicketId
    order_id: OrderId

    @classmethod
    def create(cls, ticket_id: TicketId, order_id: OrderId) -> ItemPrepared:
        return cls(
            event_id=uuid4(),
            occurred_at=datetime.now(),
            ticket_id=ticket_id,
            order_id=order_id,
        )


@dataclass(frozen=True)
class TicketReady(DomainEvent):
    ticket_id: TicketId
    order_id: OrderId

    @classmethod
    def create(cls, ticket_id: TicketId, order_id: OrderId) -> TicketReady:
        return cls(
            event_id=uuid4(),
            occurred_at=datetime.now(),
            ticket_id=ticket_id,
            order_id=order_id,
        )
