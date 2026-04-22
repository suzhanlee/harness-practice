from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import List
from uuid import UUID, uuid4

from .value_objects import Money, OrderId, SplitPaymentId


class PaymentAttemptStatus(Enum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"


@dataclass
class PaymentAttempt:
    attempt_id: UUID
    authorized_amount: Money
    status: PaymentAttemptStatus

    @classmethod
    def create(cls, authorized_amount: Money) -> PaymentAttempt:
        return cls(
            attempt_id=uuid4(),
            authorized_amount=authorized_amount,
            status=PaymentAttemptStatus.AUTHORIZED,
        )


@dataclass
class SplitPayment:
    split_payment_id: SplitPaymentId
    order_id: OrderId
    target_amount: Money
    _attempts: List[PaymentAttempt] = field(default_factory=list)
    is_finalized: bool = False
    _pending_events: List = field(default_factory=list)

    @classmethod
    def create(cls, order_id: OrderId, target_amount: Money) -> SplitPayment:
        return cls(
            split_payment_id=SplitPaymentId.generate(),
            order_id=order_id,
            target_amount=target_amount,
        )

    @property
    def attempts(self) -> List[PaymentAttempt]:
        return list(self._attempts)

    @property
    def authorized_total(self) -> Money:
        total = Money(Decimal("0"), self.target_amount.currency)
        for attempt in self._attempts:
            if attempt.status == PaymentAttemptStatus.AUTHORIZED:
                total = total + attempt.authorized_amount
        return total

    @property
    def remaining_amount(self) -> Money:
        authorized = self.authorized_total
        remaining = self.target_amount.amount - authorized.amount
        return Money(max(Decimal("0"), remaining), self.target_amount.currency)

    @property
    def is_fully_paid(self) -> bool:
        return self.authorized_total.amount >= self.target_amount.amount

    def add_attempt(self, authorized_amount: Money) -> PaymentAttempt:
        if self.is_finalized:
            raise ValueError("이미 완납된 분할 결제에는 시도를 추가할 수 없습니다.")
        new_total = self.authorized_total.amount + authorized_amount.amount
        if new_total > self.target_amount.amount:
            raise ValueError(
                f"결제 금액 합계({new_total})가 목표 금액({self.target_amount.amount})을 초과할 수 없습니다."
            )
        attempt = PaymentAttempt.create(authorized_amount)
        self._attempts.append(attempt)
        return attempt

    def finalize(self) -> None:
        if not self.is_fully_paid:
            raise ValueError(
                f"완납되지 않았습니다. 남은 금액: {self.remaining_amount.amount} {self.remaining_amount.currency}"
            )
        self.is_finalized = True
        # OrderPaid event stub — OrderPaid domain event not yet defined
        self._pending_events.append({"type": "OrderPaid", "order_id": str(self.order_id.value)})

    @property
    def pending_events(self) -> List:
        return list(self._pending_events)
