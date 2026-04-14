import pytest
from decimal import Decimal

from kiosk.domain.models.payment import Payment, PaymentMethod, PaymentStatus
from kiosk.domain.models.value_objects import Money, OrderId


class TestPayment:
    def _make_payment(self, method=PaymentMethod.CARD):
        return Payment.create(
            order_id=OrderId.generate(),
            amount=Money(Decimal("5000")),
            method=method,
        )

    def test_create_payment(self):
        p = self._make_payment()
        assert p.status == PaymentStatus.PENDING
        assert p.method == PaymentMethod.CARD
        assert p.amount.amount == Decimal("5000")

    def test_complete(self):
        p = self._make_payment()
        p.complete()
        assert p.status == PaymentStatus.COMPLETED

    def test_complete_non_pending_raises(self):
        p = self._make_payment()
        p.complete()
        with pytest.raises(ValueError, match="대기중"):
            p.complete()

    def test_fail(self):
        p = self._make_payment()
        p.fail()
        assert p.status == PaymentStatus.FAILED

    def test_fail_non_pending_raises(self):
        p = self._make_payment()
        p.complete()
        with pytest.raises(ValueError, match="대기중"):
            p.fail()

    def test_refund(self):
        p = self._make_payment()
        p.complete()
        p.refund()
        assert p.status == PaymentStatus.REFUNDED

    def test_refund_non_completed_raises(self):
        p = self._make_payment()
        with pytest.raises(ValueError, match="완료된"):
            p.refund()

    def test_all_payment_methods(self):
        for method in PaymentMethod:
            p = self._make_payment(method)
            assert p.method == method
