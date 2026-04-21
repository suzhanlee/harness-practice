"""End-to-end integration tests for the Kitchen Display System flow.

Scenario:
    주문 확정 → KitchenTicket RECEIVED 검증 → start_cooking → mark_ready → Notification READY 검증
"""
import pytest
from decimal import Decimal

from kiosk.domain.models.order import Order, OrderItem
from kiosk.domain.models.value_objects import OrderId, MenuItemId, Money
from kiosk.domain.models.kitchen_ticket import TicketStatus
from kiosk.domain.events.order_events import OrderConfirmed
from kiosk.domain.events.kitchen_events import TicketReady
from kiosk.infrastructure.repositories.in_memory_order_repository import InMemoryOrderRepository
from kiosk.infrastructure.repositories.in_memory_kitchen_ticket_repository import InMemoryKitchenTicketRepository
from kiosk.infrastructure.repositories.in_memory_notification_repository import InMemoryNotificationRepository
from kiosk.infrastructure.events.fake_dispatcher import FakeDispatcher
from kiosk.application.event_handlers.kitchen_order_handler import KitchenOrderHandler
from kiosk.application.event_handlers.customer_notification_handler import CustomerNotificationHandler
from kiosk.application.use_cases.confirm_order import ConfirmOrderUseCase
from kiosk.application.use_cases.mark_item_prepared import StartCookingUseCase, MarkItemPreparedUseCase


def _make_order_with_item(name="불고기버거", price="5500", qty=1):
    order = Order.create()
    item = OrderItem(
        menu_item_id=MenuItemId.generate(),
        name=name,
        unit_price=Money(Decimal(price)),
        quantity=qty,
    )
    order.add_item(item)
    return order


class TestKitchenFlowIntegration:
    def setup_method(self):
        self.order_repo = InMemoryOrderRepository()
        self.kitchen_ticket_repo = InMemoryKitchenTicketRepository()
        self.notification_repo = InMemoryNotificationRepository()
        self.dispatcher = FakeDispatcher()

        # Register handlers
        kitchen_handler = KitchenOrderHandler(self.kitchen_ticket_repo)
        notification_handler = CustomerNotificationHandler(self.notification_repo)
        self.dispatcher.register(OrderConfirmed, kitchen_handler.handle)
        self.dispatcher.register(TicketReady, notification_handler.handle)

        self.confirm_order = ConfirmOrderUseCase(self.order_repo, self.dispatcher)
        self.start_cooking = StartCookingUseCase(self.kitchen_ticket_repo)
        self.mark_item_prepared = MarkItemPreparedUseCase(self.kitchen_ticket_repo, self.dispatcher)

    def test_confirm_order_creates_kitchen_ticket_in_received_status(self):
        order = _make_order_with_item()
        self.order_repo.save(order)

        self.confirm_order.execute(str(order.id.value))

        tickets = self.kitchen_ticket_repo.find_by_status(TicketStatus.RECEIVED)
        assert len(tickets) == 1
        assert str(tickets[0].order_id.value) == str(order.id.value)

    def test_confirm_order_dispatches_order_confirmed_event(self):
        order = _make_order_with_item()
        self.order_repo.save(order)

        self.confirm_order.execute(str(order.id.value))

        order_confirmed_events = [e for e in self.dispatcher.received if isinstance(e, OrderConfirmed)]
        assert len(order_confirmed_events) == 1

    def test_start_cooking_transitions_ticket_to_cooking(self):
        order = _make_order_with_item()
        self.order_repo.save(order)
        self.confirm_order.execute(str(order.id.value))

        tickets = self.kitchen_ticket_repo.find_by_status(TicketStatus.RECEIVED)
        ticket_id = str(tickets[0].id.value)

        result = self.start_cooking.execute(ticket_id)

        assert result.status == TicketStatus.COOKING.value
        cooking_tickets = self.kitchen_ticket_repo.find_by_status(TicketStatus.COOKING)
        assert len(cooking_tickets) == 1

    def test_mark_ready_transitions_ticket_to_ready(self):
        order = _make_order_with_item()
        self.order_repo.save(order)
        self.confirm_order.execute(str(order.id.value))

        tickets = self.kitchen_ticket_repo.find_by_status(TicketStatus.RECEIVED)
        ticket_id = str(tickets[0].id.value)
        self.start_cooking.execute(ticket_id)

        result = self.mark_item_prepared.execute(ticket_id)

        assert result.status == TicketStatus.READY.value

    def test_mark_ready_triggers_customer_notification(self):
        order = _make_order_with_item()
        self.order_repo.save(order)
        self.confirm_order.execute(str(order.id.value))

        tickets = self.kitchen_ticket_repo.find_by_status(TicketStatus.RECEIVED)
        ticket_id = str(tickets[0].id.value)
        self.start_cooking.execute(ticket_id)
        self.mark_item_prepared.execute(ticket_id)

        notifications = self.notification_repo.find_all()
        assert len(notifications) == 1
        assert "준비 완료" in notifications[0].message

    def test_full_flow_end_to_end(self):
        """주문 확정 → RECEIVED → 조리시작(COOKING) → 준비완료(READY) → Notification 생성까지 전체 흐름."""
        order = _make_order_with_item(name="콜라", price="2000", qty=2)
        self.order_repo.save(order)

        # 1. 주문 확정
        confirm_result = self.confirm_order.execute(str(order.id.value))
        assert confirm_result.status == "확인됨"

        # 2. KitchenTicket RECEIVED 검증
        received_tickets = self.kitchen_ticket_repo.find_by_status(TicketStatus.RECEIVED)
        assert len(received_tickets) == 1
        ticket = received_tickets[0]
        assert ticket.items[0] == ("콜라", 2)
        ticket_id = str(ticket.id.value)

        # 3. 조리 시작
        cook_result = self.start_cooking.execute(ticket_id)
        assert cook_result.status == TicketStatus.COOKING.value

        # 4. 준비 완료
        ready_result = self.mark_item_prepared.execute(ticket_id)
        assert ready_result.status == TicketStatus.READY.value

        # 5. Notification READY 검증
        notifications = self.notification_repo.find_all()
        assert len(notifications) == 1
        assert "준비 완료" in notifications[0].message

    def test_fake_dispatcher_accumulates_all_events(self):
        """FakeDispatcher가 OrderConfirmed와 TicketReady 이벤트를 모두 축적하는지 검증."""
        order = _make_order_with_item()
        self.order_repo.save(order)
        self.confirm_order.execute(str(order.id.value))

        tickets = self.kitchen_ticket_repo.find_by_status(TicketStatus.RECEIVED)
        ticket_id = str(tickets[0].id.value)
        self.start_cooking.execute(ticket_id)
        self.mark_item_prepared.execute(ticket_id)

        event_types = [type(e).__name__ for e in self.dispatcher.received]
        assert "OrderConfirmed" in event_types
        assert "TicketReady" in event_types
