from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from .base import DomainEvent
from kiosk.domain.models.value_objects import OrderId, SplitPaymentId, CouponId, Money


@dataclass(frozen=True)
class OrderPaid(DomainEvent):
    order_id: OrderId
    split_payment_id: SplitPaymentId
    total_amount: Money

    @classmethod
    def from_split_payment(
        cls,
        split_payment,
        order_id: OrderId,
        occurred_at: datetime,
    ) -> OrderPaid:
        return cls(
            event_id=uuid4(),
            occurred_at=occurred_at,
            order_id=order_id,
            split_payment_id=split_payment.split_payment_id,
            total_amount=split_payment.target_amount,
        )


@dataclass(frozen=True)
class CouponRedeemed(DomainEvent):
    coupon_id: CouponId
    order_id: OrderId
    discount_amount: Money

    @classmethod
    def from_coupon(
        cls,
        coupon,
        order_id: OrderId,
        discount_amount: Money,
        occurred_at: datetime,
    ) -> CouponRedeemed:
        return cls(
            event_id=uuid4(),
            occurred_at=occurred_at,
            coupon_id=coupon.id,
            order_id=order_id,
            discount_amount=discount_amount,
        )
