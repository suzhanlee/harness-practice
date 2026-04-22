from dataclasses import dataclass
from decimal import Decimal

from kiosk.domain.models.value_objects import Money, SplitPaymentId
from kiosk.domain.repositories.split_payment_repository import SplitPaymentRepository


@dataclass(frozen=True)
class AddPaymentAttemptResult:
    attempt_id: str
    authorized_amount: str
    remaining_amount: str
    is_fully_paid: bool


class AddPaymentAttemptUseCase:
    def __init__(self, split_payment_repo: SplitPaymentRepository):
        self.split_payment_repo = split_payment_repo

    def execute(self, split_payment_id: str, authorized_amount: str) -> AddPaymentAttemptResult:
        split_payment = self.split_payment_repo.find_by_id(
            SplitPaymentId.from_str(split_payment_id)
        )
        if split_payment is None:
            raise ValueError(f"분할 결제를 찾을 수 없습니다: {split_payment_id}")

        amount = Money(Decimal(authorized_amount), split_payment.target_amount.currency)
        attempt = split_payment.add_attempt(amount)
        self.split_payment_repo.save(split_payment)

        return AddPaymentAttemptResult(
            attempt_id=str(attempt.attempt_id),
            authorized_amount=str(attempt.authorized_amount.amount),
            remaining_amount=str(split_payment.remaining_amount.amount),
            is_fully_paid=split_payment.is_fully_paid,
        )
