from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional

from kiosk.domain.models.kitchen_ticket import KitchenTicket, TicketId, TicketStatus


class KitchenTicketRepository(ABC):
    @abstractmethod
    def save(self, ticket: KitchenTicket) -> None: ...

    @abstractmethod
    def find_by_id(self, ticket_id: TicketId) -> Optional[KitchenTicket]: ...

    @abstractmethod
    def find_by_status(self, status: TicketStatus) -> List[KitchenTicket]: ...
