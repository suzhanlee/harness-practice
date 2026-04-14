from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from .value_objects import PaymentId, OrderId, Money


class PaymentMethod(Enum):
    CARD = "카드"
    CASH = "현금"
    MOBILE = "모바일"


class PaymentStatus(Enum):
    PENDING = "대기중"
    COMPLETED = "완료"
    FAILED = "실패"
    REFUNDED = "환불됨"


@dataclass
class Payment:
    id: PaymentId
    order_id: OrderId
    amount: Money
    method: PaymentMethod
    status: PaymentStatus = PaymentStatus.PENDING

    @classmethod
    def create(cls, order_id: OrderId, amount: Money, method: PaymentMethod) -> Payment:
        return cls(
            id=PaymentId.generate(),
            order_id=order_id,
            amount=amount,
            method=method,
        )

    def complete(self):
        if self.status != PaymentStatus.PENDING:
            raise ValueError("대기중 상태의 결제만 완료할 수 있습니다.")
        self.status = PaymentStatus.COMPLETED

    def fail(self):
        if self.status != PaymentStatus.PENDING:
            raise ValueError("대기중 상태의 결제만 실패 처리할 수 있습니다.")
        self.status = PaymentStatus.FAILED

    def refund(self):
        if self.status != PaymentStatus.COMPLETED:
            raise ValueError("완료된 결제만 환불할 수 있습니다.")
        self.status = PaymentStatus.REFUNDED
