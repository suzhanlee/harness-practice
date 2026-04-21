"""Tests for domain events: DomainEvent base and OrderConfirmed."""
import pytest
from decimal import Decimal
from uuid import UUID

from kiosk.domain.events.base import DomainEvent
from kiosk.domain.events.order_events import OrderConfirmed
from kiosk.domain.models.value_objects import OrderId, Money
from kiosk.domain.models.order import Order, OrderItem
from kiosk.domain.models.value_objects import MenuItemId


class TestDomainEventBase:
    def test_domain_event_has_event_id_and_occurred_at(self):
        from datetime import datetime
        from uuid import uuid4

        # OrderConfirmed is a concrete subclass we can instantiate
        order_id = OrderId.generate()
        items = [("버거", 1, Money(Decimal("5500")))]
        event = OrderConfirmed.from_order(order_id=order_id, items=items, total_amount=Money(Decimal("5500")))

        assert isinstance(event.event_id, UUID)
        assert isinstance(event.occurred_at, datetime)

    def test_domain_event_is_frozen(self):
        order_id = OrderId.generate()
        items = [("버거", 1, Money(Decimal("5500")))]
        event = OrderConfirmed.from_order(order_id=order_id, items=items, total_amount=Money(Decimal("5500")))

        with pytest.raises((TypeError, AttributeError)):
            event.event_id = None  # type: ignore


class TestOrderConfirmedEvent:
    def test_order_confirmed_contains_order_id(self):
        order_id = OrderId.generate()
        items = [("버거", 2, Money(Decimal("5500")))]
        event = OrderConfirmed.from_order(order_id=order_id, items=items, total_amount=Money(Decimal("11000")))

        assert event.order_id == order_id

    def test_order_confirmed_contains_items_and_total(self):
        order_id = OrderId.generate()
        items = [("버거", 2, Money(Decimal("5500")))]
        total = Money(Decimal("11000"))
        event = OrderConfirmed.from_order(order_id=order_id, items=items, total_amount=total)

        assert event.items == tuple(items)
        assert event.total_amount == total

    def test_order_confirm_appends_event_to_pending(self):
        order = Order.create()
        item = OrderItem(
            menu_item_id=MenuItemId.generate(),
            name="버거",
            unit_price=Money(Decimal("5500")),
            quantity=1,
        )
        order.add_item(item)
        order.confirm()

        events = order.pull_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], OrderConfirmed)

    def test_pull_domain_events_clears_pending(self):
        order = Order.create()
        item = OrderItem(
            menu_item_id=MenuItemId.generate(),
            name="버거",
            unit_price=Money(Decimal("5500")),
            quantity=1,
        )
        order.add_item(item)
        order.confirm()

        order.pull_domain_events()  # first pull
        events_second = order.pull_domain_events()  # second pull should be empty
        assert events_second == []
