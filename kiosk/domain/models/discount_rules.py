from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

from .value_objects import (
    AbstractDiscountRule,
    FixedDiscountRule,
    MemberGrade,
    Money,
    PercentageDiscountRule,
)


@dataclass(frozen=True)
class VipGradeDiscountRule(AbstractDiscountRule):
    """VIP 등급 회원에게 적용되는 퍼센트 할인 규칙."""

    priority: ClassVar[int] = 10
    grade: MemberGrade

    def calculate(self, original: Money) -> Money:
        earn_rate = MemberGrade.earn_rate(self.grade)
        delegate = PercentageDiscountRule(percent=earn_rate)
        return delegate.calculate(original)


@dataclass(frozen=True)
class CouponDiscountRule(AbstractDiscountRule):
    """쿠폰을 위임하는 할인 규칙."""

    priority: ClassVar[int] = 20
    coupon_discount_amount: Money

    def calculate(self, original: Money) -> Money:
        delegate = FixedDiscountRule(amount=self.coupon_discount_amount)
        return delegate.calculate(original)


@dataclass(frozen=True)
class PointRedemptionRule(AbstractDiscountRule):
    """포인트 차감 할인 규칙."""

    priority: ClassVar[int] = 30
    points_to_redeem: Money

    def calculate(self, original: Money) -> Money:
        delegate = FixedDiscountRule(amount=self.points_to_redeem)
        return delegate.calculate(original)
