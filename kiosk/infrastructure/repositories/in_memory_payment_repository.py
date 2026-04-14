from typing import Dict, List, Optional

from ...domain.models.payment import Payment
from ...domain.models.value_objects import PaymentId, OrderId
from ...domain.repositories.payment_repository import PaymentRepository


class InMemoryPaymentRepository(PaymentRepository):
    def __init__(self):
        self._store: Dict[PaymentId, Payment] = {}

    def save(self, payment: Payment) -> None:
        self._store[payment.id] = payment

    def find_by_id(self, payment_id: PaymentId) -> Optional[Payment]:
        return self._store.get(payment_id)

    def find_by_order_id(self, order_id: OrderId) -> Optional[Payment]:
        for payment in self._store.values():
            if payment.order_id == order_id:
                return payment
        return None
