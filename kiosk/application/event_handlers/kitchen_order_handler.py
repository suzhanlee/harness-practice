from __future__ import annotations

from kiosk.domain.events.order_events import OrderConfirmed
from kiosk.domain.models.kitchen_ticket import KitchenTicket
from kiosk.domain.repositories.kitchen_ticket_repository import KitchenTicketRepository


class KitchenOrderHandler:
    def __init__(self, kitchen_ticket_repo: KitchenTicketRepository):
        self._kitchen_ticket_repo = kitchen_ticket_repo

    def handle(self, event: OrderConfirmed) -> None:
        items = [(name, quantity) for name, quantity, _price in event.items]
        ticket = KitchenTicket.create(order_id=event.order_id, items=items)
        self._kitchen_ticket_repo.save(ticket)
