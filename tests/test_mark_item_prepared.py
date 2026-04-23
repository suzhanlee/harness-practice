"""Tests for MarkItemPreparedUseCase and StartCookingUseCase."""
import pytest

from kiosk.domain.models.kitchen_ticket import KitchenTicket, TicketStatus
from kiosk.domain.models.value_objects import OrderId
from kiosk.infrastructure.repositories.in_memory_kitchen_ticket_repository import InMemoryKitchenTicketRepository
from kiosk.application.use_cases.mark_item_prepared import StartCookingUseCase, MarkItemPreparedUseCase


def _make_ticket():
    return KitchenTicket.create(
        order_id=OrderId.generate(),
        items=[("불고기버거", 2)],
    )


class TestStartCookingUseCase:
    def setup_method(self):
        self.kitchen_ticket_repo = InMemoryKitchenTicketRepository()
        self.use_case = StartCookingUseCase(self.kitchen_ticket_repo)

    def test_start_cooking_transitions_to_cooking(self):
        ticket = _make_ticket()
        self.kitchen_ticket_repo.save(ticket)

        result = self.use_case.execute(str(ticket.id.value))

        assert result.status == TicketStatus.COOKING.value

    def test_start_cooking_persists_status_change(self):
        ticket = _make_ticket()
        self.kitchen_ticket_repo.save(ticket)

        self.use_case.execute(str(ticket.id.value))

        saved = self.kitchen_ticket_repo.find_by_id(ticket.id)
        assert saved.status == TicketStatus.COOKING

    def test_start_cooking_raises_for_nonexistent_ticket(self):
        from kiosk.domain.models.kitchen_ticket import TicketId
        fake_id = str(TicketId.generate().value)
        with pytest.raises(ValueError):
            self.use_case.execute(fake_id)

    def test_start_cooking_raises_if_not_received(self):
        ticket = _make_ticket()
        ticket.start_cooking()  # RECEIVED -> COOKING
        self.kitchen_ticket_repo.save(ticket)

        with pytest.raises(ValueError):
            self.use_case.execute(str(ticket.id.value))


class TestMarkItemPreparedUseCase:
    def setup_method(self):
        self.kitchen_ticket_repo = InMemoryKitchenTicketRepository()
        self.use_case = MarkItemPreparedUseCase(self.kitchen_ticket_repo)

    def test_mark_ready_transitions_to_ready(self):
        ticket = _make_ticket()
        ticket.start_cooking()
        self.kitchen_ticket_repo.save(ticket)

        result = self.use_case.execute(str(ticket.id.value))

        assert result.status == TicketStatus.READY.value

    def test_mark_ready_persists_status_change(self):
        ticket = _make_ticket()
        ticket.start_cooking()
        self.kitchen_ticket_repo.save(ticket)

        self.use_case.execute(str(ticket.id.value))

        saved = self.kitchen_ticket_repo.find_by_id(ticket.id)
        assert saved.status == TicketStatus.READY

    def test_mark_ready_raises_for_nonexistent_ticket(self):
        from kiosk.domain.models.kitchen_ticket import TicketId
        fake_id = str(TicketId.generate().value)
        with pytest.raises(ValueError):
            self.use_case.execute(fake_id)

    def test_mark_ready_raises_if_not_cooking(self):
        ticket = _make_ticket()
        # RECEIVED, not COOKING
        self.kitchen_ticket_repo.save(ticket)

        with pytest.raises(ValueError):
            self.use_case.execute(str(ticket.id.value))

    def test_mark_ready_returns_dto_with_items(self):
        ticket = _make_ticket()
        ticket.start_cooking()
        self.kitchen_ticket_repo.save(ticket)

        result = self.use_case.execute(str(ticket.id.value))

        assert result.items == [("불고기버거", 2)]
