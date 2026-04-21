"""Tests for ConfirmOrderUseCase and KitchenOrderHandler integration."""
import pytest
from decimal import Decimal

from kiosk.domain.models.order import Order, OrderItem, OrderStatus
from kiosk.domain.models.value_objects import OrderId, MenuItemId, Money
from kiosk.domain.events.order_events import OrderConfirmed
from kiosk.domain.models.kitchen_ticket import TicketStatus
from kiosk.infrastructure.repositories.in_memory_order_repository import InMemoryOrderRepository
from kiosk.infrastructure.repositories.in_memory_kitchen_ticket_repository import InMemoryKitchenTicketRepository
from kiosk.application.events.dispatcher import EventDispatcher
from kiosk.application.event_handlers.kitchen_order_handler import KitchenOrderHandler
from kiosk.application.use_cases.confirm_order import ConfirmOrderUseCase


def _make_order_with_item():
    order = Order.create()
    item = OrderItem(
        menu_item_id=MenuItemId.generate(),
        name="불고기버거",
        unit_price=Money(Decimal("5500")),
        quantity=2,
    )
    order.add_item(item)
    return order


class TestConfirmOrderUseCase:
    def setup_method(self):
        self.order_repo = InMemoryOrderRepository()
        self.kitchen_ticket_repo = InMemoryKitchenTicketRepository()
        self.dispatcher = EventDispatcher()
        handler = KitchenOrderHandler(self.kitchen_ticket_repo)
        self.dispatcher.register(OrderConfirmed, handler.handle)
        self.use_case = ConfirmOrderUseCase(self.order_repo, self.dispatcher)

    def test_confirm_order_returns_confirmed_status(self):
        order = _make_order_with_item()
        self.order_repo.save(order)

        result = self.use_case.execute(str(order.id.value))

        assert result.status == OrderStatus.CONFIRMED.value

    def test_confirm_order_returns_order_dto_with_items(self):
        order = _make_order_with_item()
        self.order_repo.save(order)

        result = self.use_case.execute(str(order.id.value))

        assert len(result.items) == 1
        assert result.items[0].name == "불고기버거"
        assert result.items[0].quantity == 2

    def test_confirm_order_creates_kitchen_ticket(self):
        order = _make_order_with_item()
        self.order_repo.save(order)

        self.use_case.execute(str(order.id.value))

        tickets = self.kitchen_ticket_repo.find_by_status(TicketStatus.RECEIVED)
        assert len(tickets) == 1
        assert str(tickets[0].order_id.value) == str(order.id.value)

    def test_confirm_order_ticket_contains_items(self):
        order = _make_order_with_item()
        self.order_repo.save(order)

        self.use_case.execute(str(order.id.value))

        tickets = self.kitchen_ticket_repo.find_by_status(TicketStatus.RECEIVED)
        ticket = tickets[0]
        assert len(ticket.items) == 1
        assert ticket.items[0] == ("불고기버거", 2)

    def test_confirm_order_pulls_events_from_order(self):
        order = _make_order_with_item()
        self.order_repo.save(order)

        self.use_case.execute(str(order.id.value))

        # After dispatch, pending events should have been cleared
        saved_order = self.order_repo.find_by_id(order.id)
        # pull_domain_events already cleared inside use case; order in repo is the same object
        assert saved_order.pull_domain_events() == []

    def test_confirm_order_raises_for_nonexistent_order(self):
        with pytest.raises(ValueError):
            self.use_case.execute(str(OrderId.generate().value))

    def test_confirm_order_raises_for_empty_order(self):
        order = Order.create()
        self.order_repo.save(order)

        with pytest.raises(ValueError):
            self.use_case.execute(str(order.id.value))
