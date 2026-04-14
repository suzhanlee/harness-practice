from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4


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
