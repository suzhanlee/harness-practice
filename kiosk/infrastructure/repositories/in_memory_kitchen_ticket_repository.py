from __future__ import annotations
from typing import Dict, List, Optional

from kiosk.domain.models.kitchen_ticket import KitchenTicket, TicketId, TicketStatus
from kiosk.domain.repositories.kitchen_ticket_repository import KitchenTicketRepository


class InMemoryKitchenTicketRepository(KitchenTicketRepository):
    def __init__(self):
        self._tickets: Dict[TicketId, KitchenTicket] = {}

    def save(self, ticket: KitchenTicket) -> None:
        self._tickets[ticket.id] = ticket

    def find_by_id(self, ticket_id: TicketId) -> Optional[KitchenTicket]:
        return self._tickets.get(ticket_id)

    def find_by_status(self, status: TicketStatus) -> List[KitchenTicket]:
        return [t for t in self._tickets.values() if t.status == status]
