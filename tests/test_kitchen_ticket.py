"""Tests for KitchenTicket domain model and repository."""
import pytest

from kiosk.domain.models.kitchen_ticket import KitchenTicket, TicketStatus, TicketId
from kiosk.domain.models.value_objects import OrderId
from kiosk.infrastructure.repositories.in_memory_kitchen_ticket_repository import InMemoryKitchenTicketRepository


class TestKitchenTicketCreation:
    def test_create_ticket_with_received_status(self):
        order_id = OrderId.generate()
        items = [("버거", 1), ("콜라", 2)]
        ticket = KitchenTicket.create(order_id=order_id, items=items)

        assert ticket.status == TicketStatus.RECEIVED
        assert ticket.order_id == order_id
        assert ticket.items == items
        assert isinstance(ticket.id, TicketId)

    def test_create_generates_unique_ids(self):
        order_id = OrderId.generate()
        t1 = KitchenTicket.create(order_id=order_id, items=[])
        t2 = KitchenTicket.create(order_id=order_id, items=[])
        assert t1.id != t2.id


class TestKitchenTicketStateTransitions:
    def _make_ticket(self):
        return KitchenTicket.create(order_id=OrderId.generate(), items=[("버거", 1)])

    def test_start_cooking_transitions_to_cooking(self):
        ticket = self._make_ticket()
        ticket.start_cooking()
        assert ticket.status == TicketStatus.COOKING

    def test_mark_ready_transitions_to_ready(self):
        ticket = self._make_ticket()
        ticket.start_cooking()
        ticket.mark_ready()
        assert ticket.status == TicketStatus.READY

    def test_mark_served_transitions_to_served(self):
        ticket = self._make_ticket()
        ticket.start_cooking()
        ticket.mark_ready()
        ticket.mark_served()
        assert ticket.status == TicketStatus.SERVED

    def test_start_cooking_raises_if_not_received(self):
        ticket = self._make_ticket()
        ticket.start_cooking()
        with pytest.raises(ValueError):
            ticket.start_cooking()

    def test_mark_ready_raises_if_not_cooking(self):
        ticket = self._make_ticket()
        with pytest.raises(ValueError):
            ticket.mark_ready()

    def test_mark_served_raises_if_not_ready(self):
        ticket = self._make_ticket()
        ticket.start_cooking()
        with pytest.raises(ValueError):
            ticket.mark_served()


class TestInMemoryKitchenTicketRepository:
    def test_save_and_find_by_id(self):
        repo = InMemoryKitchenTicketRepository()
        ticket = KitchenTicket.create(order_id=OrderId.generate(), items=[("버거", 1)])
        repo.save(ticket)

        found = repo.find_by_id(ticket.id)
        assert found is ticket

    def test_find_by_id_returns_none_if_not_found(self):
        repo = InMemoryKitchenTicketRepository()
        result = repo.find_by_id(TicketId.generate())
        assert result is None

    def test_find_by_status(self):
        repo = InMemoryKitchenTicketRepository()
        t1 = KitchenTicket.create(order_id=OrderId.generate(), items=[])
        t2 = KitchenTicket.create(order_id=OrderId.generate(), items=[])
        t2.start_cooking()
        repo.save(t1)
        repo.save(t2)

        received = repo.find_by_status(TicketStatus.RECEIVED)
        cooking = repo.find_by_status(TicketStatus.COOKING)

        assert t1 in received
        assert t2 not in received
        assert t2 in cooking
