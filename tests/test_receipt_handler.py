from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from kiosk.application.event_handlers.logging_audit_handler import LoggingAuditHandler
from kiosk.application.event_handlers.order_settlement_handler import OrderSettlementHandler
from kiosk.domain.events.payment_events import CouponRedeemed, OrderPaid
from kiosk.domain.models.order import Order, OrderItem, OrderStatus
from kiosk.domain.models.receipt import ReceiptRecord
from kiosk.domain.models.value_objects import (
    CouponId,
    MenuItemId,
    Money,
    OrderId,
    SplitPaymentId,
)
from kiosk.infrastructure.repositories.in_memory_order_repository import (
    InMemoryOrderRepository,
)
from kiosk.infrastructure.repositories.in_memory_receipt_repository import (
    InMemoryReceiptRepository,
)


def _make_confirmed_order() -> Order:
    order = Order.create()
    item = OrderItem(
        menu_item_id=MenuItemId.generate(),
        name="테스트버거",
        unit_price=Money(Decimal("5000")),
        quantity=2,
    )
    order.add_item(item)
    order.confirm()
    return order


def _make_order_paid_event(order: Order) -> OrderPaid:
    split_payment_id = SplitPaymentId.generate()

    class _FakeSplitPayment:
        split_payment_id = SplitPaymentId.generate()
        target_amount = order.total_amount

    return OrderPaid.from_split_payment(
        split_payment=_FakeSplitPayment(),
        order_id=order.id,
        occurred_at=datetime.utcnow(),
    )


class TestOrderSettlementHandler:
    def test_receipt_record_created_and_saved(self):
        order_repo = InMemoryOrderRepository()
        receipt_repo = InMemoryReceiptRepository()
        handler = OrderSettlementHandler(order_repo, receipt_repo)

        order = _make_confirmed_order()
        order_repo.save(order)
        event = _make_order_paid_event(order)

        handler.handle(event)

        receipt = receipt_repo.find_by_order_id(str(order.id.value))
        assert receipt is not None
        assert isinstance(receipt, ReceiptRecord)
        assert receipt.order_id == str(order.id.value)
        assert receipt.total_amount == str(order.total_amount.amount)

    def test_order_mark_paid_called(self):
        order_repo = InMemoryOrderRepository()
        receipt_repo = InMemoryReceiptRepository()
        handler = OrderSettlementHandler(order_repo, receipt_repo)

        order = _make_confirmed_order()
        order_repo.save(order)
        assert order.status == OrderStatus.CONFIRMED

        event = _make_order_paid_event(order)
        handler.handle(event)

        updated_order = order_repo.find_by_id(order.id)
        assert updated_order.status == OrderStatus.PAID


class TestLoggingAuditHandler:
    def test_coupon_redeemed_emits_warning_log(self, caplog):
        handler = LoggingAuditHandler()
        coupon_id = CouponId.generate()
        order_id = OrderId.generate()
        discount_amount = Money(Decimal("1000"))

        event = CouponRedeemed(
            event_id=uuid4(),
            occurred_at=datetime.utcnow(),
            coupon_id=coupon_id,
            order_id=order_id,
            discount_amount=discount_amount,
        )

        with caplog.at_level(logging.WARNING, logger="kiosk.application.event_handlers.logging_audit_handler"):
            handler.handle(event)

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelno == logging.WARNING
        assert str(coupon_id.value) in record.getMessage()
        assert str(order_id.value) in record.getMessage()
        assert str(discount_amount.amount) in record.getMessage()
