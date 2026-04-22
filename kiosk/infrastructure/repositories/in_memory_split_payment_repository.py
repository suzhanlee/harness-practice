from typing import Dict, Optional

from kiosk.domain.models.split_payment import SplitPayment
from kiosk.domain.models.value_objects import SplitPaymentId, OrderId
from kiosk.domain.repositories.split_payment_repository import SplitPaymentRepository


class InMemorySplitPaymentRepository(SplitPaymentRepository):

    def __init__(self):
        self._store: Dict[SplitPaymentId, SplitPayment] = {}

    def save(self, split_payment: SplitPayment) -> None:
        self._store[split_payment.split_payment_id] = split_payment

    def find_by_id(self, split_payment_id: SplitPaymentId) -> Optional[SplitPayment]:
        return self._store.get(split_payment_id)

    def find_by_order_id(self, order_id: OrderId) -> Optional[SplitPayment]:
        for sp in self._store.values():
            if sp.order_id == order_id:
                return sp
        return None
