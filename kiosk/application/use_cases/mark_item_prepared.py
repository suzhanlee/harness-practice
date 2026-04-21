from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from kiosk.domain.models.kitchen_ticket import TicketId, TicketStatus
from kiosk.domain.repositories.kitchen_ticket_repository import KitchenTicketRepository


@dataclass
class KitchenTicketDTO:
    ticket_id: str
    order_id: str
    status: str
    items: list


class StartCookingUseCase:
    def __init__(self, kitchen_ticket_repo: KitchenTicketRepository):
        self._kitchen_ticket_repo = kitchen_ticket_repo

    def execute(self, ticket_id: str) -> KitchenTicketDTO:
        ticket = self._kitchen_ticket_repo.find_by_id(TicketId(value=_parse_uuid(ticket_id)))
        if ticket is None:
            raise ValueError(f"티켓을 찾을 수 없습니다: {ticket_id}")
        ticket.start_cooking()
        self._kitchen_ticket_repo.save(ticket)
        return _to_dto(ticket)


class MarkItemPreparedUseCase:
    def __init__(self, kitchen_ticket_repo: KitchenTicketRepository, dispatcher=None):
        self._kitchen_ticket_repo = kitchen_ticket_repo
        self._dispatcher = dispatcher

    def execute(self, ticket_id: str) -> KitchenTicketDTO:
        ticket = self._kitchen_ticket_repo.find_by_id(TicketId(value=_parse_uuid(ticket_id)))
        if ticket is None:
            raise ValueError(f"티켓을 찾을 수 없습니다: {ticket_id}")
        ticket.mark_ready()
        self._kitchen_ticket_repo.save(ticket)
        if self._dispatcher is not None:
            from kiosk.domain.events.kitchen_events import TicketReady
            event = TicketReady.create(ticket_id=ticket.id, order_id=ticket.order_id)
            self._dispatcher.dispatch([event])
        return _to_dto(ticket)


def _parse_uuid(value: str):
    from uuid import UUID
    return UUID(value)


def _to_dto(ticket) -> KitchenTicketDTO:
    return KitchenTicketDTO(
        ticket_id=str(ticket.id.value),
        order_id=str(ticket.order_id.value),
        status=ticket.status.value,
        items=list(ticket.items),
    )
