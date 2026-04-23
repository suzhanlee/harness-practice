"""Tests for EventDispatcher: register, dispatch, and static dict routing."""
import pytest

from kiosk.application.events.dispatcher import EventDispatcher
from kiosk.domain.events.base import DomainEvent
from kiosk.domain.events.order_events import OrderConfirmed
from kiosk.domain.events.kitchen_events import TicketReady
from kiosk.domain.models.value_objects import OrderId, Money
from kiosk.domain.models.kitchen_ticket import TicketId
from decimal import Decimal


def make_order_confirmed():
    return OrderConfirmed.from_order(
        order_id=OrderId.generate(),
        items=[("버거", 1, Money(Decimal("5500")))],
        total_amount=Money(Decimal("5500")),
    )


class TestEventDispatcher:
    def test_registered_handler_is_called_on_dispatch(self):
        dispatcher = EventDispatcher()
        received = []

        dispatcher.register(OrderConfirmed, lambda e: received.append(e))
        event = make_order_confirmed()
        dispatcher.dispatch([event])

        assert len(received) == 1
        assert received[0] is event

    def test_unregistered_event_type_is_silently_ignored(self):
        dispatcher = EventDispatcher()
        event = make_order_confirmed()
        # No handler registered — should not raise
        dispatcher.dispatch([event])

    def test_multiple_handlers_for_same_event_type_all_called(self):
        dispatcher = EventDispatcher()
        calls_a = []
        calls_b = []

        dispatcher.register(OrderConfirmed, lambda e: calls_a.append(e))
        dispatcher.register(OrderConfirmed, lambda e: calls_b.append(e))

        event = make_order_confirmed()
        dispatcher.dispatch([event])

        assert len(calls_a) == 1
        assert len(calls_b) == 1

    def test_dispatch_routes_to_correct_handler_by_type(self):
        dispatcher = EventDispatcher()
        confirmed_calls = []
        ready_calls = []

        dispatcher.register(OrderConfirmed, lambda e: confirmed_calls.append(e))
        dispatcher.register(TicketReady, lambda e: ready_calls.append(e))

        order_id = OrderId.generate()
        ticket_id = TicketId.generate()
        confirmed_event = make_order_confirmed()
        ready_event = TicketReady.create(ticket_id=ticket_id, order_id=order_id)

        dispatcher.dispatch([confirmed_event, ready_event])

        assert len(confirmed_calls) == 1
        assert len(ready_calls) == 1
        assert confirmed_calls[0] is confirmed_event
        assert ready_calls[0] is ready_event

    def test_dispatch_empty_list_does_nothing(self):
        dispatcher = EventDispatcher()
        called = []
        dispatcher.register(OrderConfirmed, lambda e: called.append(e))
        dispatcher.dispatch([])
        assert called == []
