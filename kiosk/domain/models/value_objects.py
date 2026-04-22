from __future__ import annotations
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import ClassVar
from uuid import UUID, uuid4
from datetime import datetime


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "KRW"

    def __post_init__(self):
        if self.amount < Decimal("0"):
            raise ValueError("금액은 0 이상이어야 합니다.")

    def __add__(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise ValueError("통화가 다릅니다.")
        return Money(self.amount + other.amount, self.currency)

    def __mul__(self, quantity: int) -> Money:
        return Money(self.amount * Decimal(quantity), self.currency)

    def __repr__(self):
        return f"{self.amount} {self.currency}"


@dataclass(frozen=True)
class MenuItemId:
    value: UUID

    @classmethod
    def generate(cls) -> MenuItemId:
        return cls(uuid4())

    @classmethod
    def from_str(cls, value: str) -> MenuItemId:
        return cls(UUID(value))


@dataclass(frozen=True)
class OrderId:
    value: UUID

    @classmethod
    def generate(cls) -> OrderId:
        return cls(uuid4())

    @classmethod
    def from_str(cls, value: str) -> OrderId:
        return cls(UUID(value))


@dataclass(frozen=True)
class PaymentId:
    value: UUID

    @classmethod
    def generate(cls) -> PaymentId:
        return cls(uuid4())


@dataclass(frozen=True)
class UserId:
    value: UUID

    @classmethod
    def generate(cls) -> UserId:
        return cls(uuid4())

    @classmethod
    def from_str(cls, value: str) -> UserId:
        return cls(UUID(value))


@dataclass(frozen=True)
class DiscountId:
    value: UUID

    @classmethod
    def generate(cls) -> DiscountId:
        return cls(uuid4())

    @classmethod
    def from_str(cls, value: str) -> DiscountId:
        return cls(UUID(value))


@dataclass(frozen=True)
class CouponCode:
    value: str

    def __post_init__(self):
        if not self.value or len(self.value.strip()) == 0:
            raise ValueError("쿠폰 코드는 비어있을 수 없습니다.")


@dataclass(frozen=True)
class DiscountRule:
    discount_type: str
    value: Decimal
    applicable_target: str

    def __post_init__(self):
        if self.discount_type not in ["fixed", "percentage"]:
            raise ValueError("할인 타입은 'fixed' 또는 'percentage'여야 합니다.")
        if self.value < Decimal("0"):
            raise ValueError("할인 값은 0 이상이어야 합니다.")
        if self.discount_type == "percentage" and self.value > Decimal("100"):
            raise ValueError("정률 할인은 100% 이하여야 합니다.")
        if self.applicable_target not in ["order", "product", "both"]:
            raise ValueError("적용 대상은 'order', 'product', 'both' 중 하나여야 합니다.")


@dataclass(frozen=True)
class Stock:
    value: int
    _unlimited: bool = field(default=False, compare=False, repr=False)

    def __post_init__(self):
        if not self._unlimited and self.value < 0:
            raise ValueError("재고는 0 이상이어야 합니다.")

    @classmethod
    def unlimited(cls) -> Stock:
        return cls(value=0, _unlimited=True)

    def is_unlimited(self) -> bool:
        return self._unlimited

    def has_enough(self, qty: int) -> bool:
        return self._unlimited or self.value >= qty

    def decrease(self, qty: int) -> None:
        if self._unlimited:
            return
        if self.value < qty:
            raise ValueError(f"재고가 부족합니다. 현재 재고: {self.value}, 요청: {qty}")
        object.__setattr__(self, 'value', self.value - qty)

    def restock(self, qty: int) -> None:
        if qty <= 0:
            raise ValueError("재고 추가량은 0보다 커야 합니다.")
        if self._unlimited:
            object.__setattr__(self, '_unlimited', False)
            object.__setattr__(self, 'value', qty)
        else:
            object.__setattr__(self, 'value', self.value + qty)


@dataclass(frozen=True)
class OrderStateSnapshot:
    status: str
    total_amount: Money
    timestamp: datetime
    item_count: int


@dataclass(frozen=True)
class CouponId:
    value: UUID

    @classmethod
    def generate(cls) -> CouponId:
        return cls(uuid4())

    @classmethod
    def from_str(cls, value: str) -> CouponId:
        return cls(UUID(value))


@dataclass(frozen=True)
class SplitPaymentId:
    value: UUID

    @classmethod
    def generate(cls) -> SplitPaymentId:
        return cls(uuid4())

    @classmethod
    def from_str(cls, value: str) -> SplitPaymentId:
        return cls(UUID(value))


@dataclass(frozen=True)
class MemberId:
    value: UUID

    @classmethod
    def generate(cls) -> MemberId:
        return cls(uuid4())

    @classmethod
    def from_str(cls, value: str) -> MemberId:
        return cls(UUID(value))


@dataclass(frozen=True)
class PointAccountId:
    value: UUID

    @classmethod
    def generate(cls) -> PointAccountId:
        return cls(uuid4())

    @classmethod
    def from_str(cls, value: str) -> PointAccountId:
        return cls(UUID(value))


class MemberGrade(Enum):
    NORMAL = "NORMAL"
    SILVER = "SILVER"
    GOLD = "GOLD"
    VIP = "VIP"

    @classmethod
    def earn_rate(cls, grade: MemberGrade) -> Decimal:
        rates = {
            cls.NORMAL: Decimal("1"),
            cls.SILVER: Decimal("2"),
            cls.GOLD: Decimal("3"),
            cls.VIP: Decimal("5"),
        }
        return rates[grade]


class InsufficientPointBalanceError(ValueError):
    """Raised when attempting to redeem more points than available balance."""


class _DiscountRuleMeta(ABCMeta):
    """Metaclass combining ABCMeta with frozen dataclass support."""


@dataclass(frozen=True)
class AbstractDiscountRule(metaclass=_DiscountRuleMeta):
    """Abstract base for all discount rules. Subclasses must implement calculate()."""

    priority: ClassVar[int] = 999

    @abstractmethod
    def calculate(self, original: Money) -> Money:
        """Return the discount amount (not the discounted price) for the given original price."""


@dataclass(frozen=True)
class FixedDiscountRule(AbstractDiscountRule):
    """Deducts a fixed monetary amount."""
    amount: Money

    def calculate(self, original: Money) -> Money:
        if self.amount.currency != original.currency:
            raise ValueError("통화가 다릅니다.")
        discount = min(self.amount.amount, original.amount)
        return Money(discount, original.currency)


@dataclass(frozen=True)
class PercentageDiscountRule(AbstractDiscountRule):
    """Deducts a percentage of the original price."""
    percent: Decimal

    def __post_init__(self):
        if self.percent < Decimal("0") or self.percent > Decimal("100"):
            raise ValueError("퍼센트는 0 이상 100 이하여야 합니다.")

    def calculate(self, original: Money) -> Money:
        discount_amount = original.amount * (self.percent / Decimal("100"))
        return Money(discount_amount, original.currency)


@dataclass(frozen=True)
class DiscountCalculation:
    """Value Object representing the result of applying a discount chain."""
    original: Money
    discount: Money
    final: Money

    @classmethod
    def compute(cls, original: Money, discount: Money) -> DiscountCalculation:
        if original.currency != discount.currency:
            raise ValueError("통화가 다릅니다.")
        raw_final = original.amount - discount.amount
        final_amount = max(Decimal("0"), raw_final)
        return cls(
            original=original,
            discount=discount,
            final=Money(final_amount, original.currency),
        )


@dataclass(frozen=True)
class DiscountChain:
    """Applies a sequence of DiscountRules in order. Caller is responsible for ordering."""
    policies: tuple

    def apply(self, original: Money) -> DiscountCalculation:
        remaining = original
        total_discount = Money(Decimal("0"), original.currency)
        for policy in self.policies:
            discount = policy.calculate(remaining)
            total_discount = total_discount + discount
            discounted_amount = max(Decimal("0"), remaining.amount - discount.amount)
            remaining = Money(discounted_amount, original.currency)
        return DiscountCalculation.compute(original, total_discount)
