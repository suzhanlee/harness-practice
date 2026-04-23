from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Set, Optional

from .value_objects import CouponId, CouponCode, OrderId, Money


class CouponExpiredError(Exception):
    """쿠폰이 만료되었을 때 발생합니다."""
    pass


class CouponUsageLimitExceededError(Exception):
    """쿠폰 사용 횟수가 초과되었을 때 발생합니다."""
    pass


class CouponAlreadyUsedError(Exception):
    """같은 주문에 이미 사용된 쿠폰일 때 발생합니다."""
    pass


@dataclass
class CouponRedeemed:
    """쿠폰 사용 이벤트."""
    coupon_id: CouponId
    order_id: OrderId
    discount_amount: Money
    occurred_at: datetime


@dataclass
class Coupon:
    id: CouponId
    code: CouponCode
    discount_amount: Money
    expires_at: datetime
    max_usage: int
    discount_type: str = "fixed"        # "fixed" | "percentage"
    discount_value: str = "0"           # raw value string (e.g. "1000" or "10")
    usage_count: int = 0
    redeemed_order_ids: Set[OrderId] = field(default_factory=set)
    version: int = 0
    _pending_events: List[CouponRedeemed] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        if self.max_usage < 1:
            raise ValueError("최대 사용 횟수는 1 이상이어야 합니다.")

    @classmethod
    def create(
        cls,
        code: str,
        discount_amount: Money,
        expires_at: datetime,
        max_usage: int,
        coupon_id: Optional[CouponId] = None,
        discount_type: str = "fixed",
        discount_value: Optional[str] = None,
    ) -> Coupon:
        raw_value = discount_value if discount_value is not None else str(discount_amount.amount)
        return cls(
            id=coupon_id or CouponId.generate(),
            code=CouponCode(code),
            discount_amount=discount_amount,
            expires_at=expires_at,
            max_usage=max_usage,
            discount_type=discount_type,
            discount_value=raw_value,
        )

    def redeem(self, order_id: OrderId, now: datetime) -> None:
        """쿠폰을 사용합니다. 원자적 전이 (불변식 검사 후 상태 변경)."""
        if now >= self.expires_at:
            raise CouponExpiredError(
                f"쿠폰이 만료되었습니다. 만료 시각: {self.expires_at}, 현재 시각: {now}"
            )
        if self.usage_count >= self.max_usage:
            raise CouponUsageLimitExceededError(
                f"쿠폰 사용 횟수를 초과하였습니다. 최대: {self.max_usage}, 현재: {self.usage_count}"
            )
        if order_id in self.redeemed_order_ids:
            raise CouponAlreadyUsedError(
                f"이미 사용된 쿠폰입니다. 주문 ID: {order_id}"
            )

        # 원자적 상태 전이
        self.usage_count += 1
        self.redeemed_order_ids.add(order_id)
        self.version += 1
        self._pending_events.append(
            CouponRedeemed(
                coupon_id=self.id,
                order_id=order_id,
                discount_amount=self.discount_amount,
                occurred_at=now,
            )
        )

    def is_usable(self, now: datetime) -> bool:
        """만료되지 않았고 사용 횟수가 남아 있으면 True."""
        if now >= self.expires_at:
            return False
        if self.usage_count >= self.max_usage:
            return False
        return True
