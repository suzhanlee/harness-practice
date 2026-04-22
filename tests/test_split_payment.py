"""Tests for SplitPayment aggregate and related infrastructure."""
import pytest
from decimal import Decimal

from kiosk.domain.models.split_payment import (
    SplitPayment,
    PaymentAttempt,
    PaymentAttemptStatus,
)
from kiosk.domain.models.value_objects import Money, OrderId, SplitPaymentId
from kiosk.infrastructure.repositories.in_memory_split_payment_repository import (
    InMemorySplitPaymentRepository,
)


@pytest.fixture
def order_id():
    return OrderId.generate()


@pytest.fixture
def target_amount():
    return Money(Decimal("10000"), "KRW")


@pytest.fixture
def split_payment(order_id, target_amount):
    return SplitPayment.create(order_id=order_id, target_amount=target_amount)


class TestSplitPaymentAddAttempt:
    def test_add_single_attempt_check_remaining(self, split_payment):
        """Add a single attempt and verify remaining amount is correct."""
        attempt = split_payment.add_attempt(Money(Decimal("4000"), "KRW"))

        assert attempt.status == PaymentAttemptStatus.AUTHORIZED
        assert attempt.authorized_amount == Money(Decimal("4000"), "KRW")
        assert split_payment.remaining_amount == Money(Decimal("6000"), "KRW")
        assert not split_payment.is_fully_paid

    def test_add_multiple_attempts_until_fully_paid(self, split_payment):
        """Add multiple attempts that together cover the target amount."""
        split_payment.add_attempt(Money(Decimal("3000"), "KRW"))
        split_payment.add_attempt(Money(Decimal("3000"), "KRW"))
        split_payment.add_attempt(Money(Decimal("4000"), "KRW"))

        assert split_payment.is_fully_paid
        assert split_payment.remaining_amount == Money(Decimal("0"), "KRW")
        assert len(split_payment.attempts) == 3

    def test_overpayment_raises_value_error(self, split_payment):
        """Adding an attempt that would exceed target_amount raises ValueError."""
        split_payment.add_attempt(Money(Decimal("8000"), "KRW"))

        with pytest.raises(ValueError):
            split_payment.add_attempt(Money(Decimal("3000"), "KRW"))


class TestSplitPaymentFinalize:
    def test_finalize_when_fully_paid_succeeds(self, split_payment):
        """finalize() succeeds when fully paid and sets is_finalized=True."""
        split_payment.add_attempt(Money(Decimal("10000"), "KRW"))

        split_payment.finalize()

        assert split_payment.is_finalized
        events = split_payment.pending_events
        assert len(events) == 1
        assert events[0]["type"] == "OrderPaid"

    def test_finalize_when_not_fully_paid_raises_value_error(self, split_payment):
        """finalize() raises ValueError when payment is incomplete."""
        split_payment.add_attempt(Money(Decimal("5000"), "KRW"))

        with pytest.raises(ValueError):
            split_payment.finalize()


class TestInMemorySplitPaymentRepository:
    def test_save_and_find_by_id(self, split_payment):
        repo = InMemorySplitPaymentRepository()
        repo.save(split_payment)

        found = repo.find_by_id(split_payment.split_payment_id)
        assert found is split_payment

    def test_find_by_order_id(self, split_payment, order_id):
        repo = InMemorySplitPaymentRepository()
        repo.save(split_payment)

        found = repo.find_by_order_id(order_id)
        assert found is split_payment

    def test_find_by_id_not_found_returns_none(self):
        repo = InMemorySplitPaymentRepository()
        result = repo.find_by_id(SplitPaymentId.generate())
        assert result is None

    def test_find_by_order_id_not_found_returns_none(self):
        repo = InMemorySplitPaymentRepository()
        result = repo.find_by_order_id(OrderId.generate())
        assert result is None
