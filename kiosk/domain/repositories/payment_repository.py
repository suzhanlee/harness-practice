from abc import ABC, abstractmethod
from typing import Optional
from ..models.payment import Payment
from ..models.value_objects import PaymentId, OrderId


class PaymentRepository(ABC):

    @abstractmethod
    def save(self, payment: Payment) -> None:
        pass

    @abstractmethod
    def find_by_id(self, payment_id: PaymentId) -> Optional[Payment]:
        pass

    @abstractmethod
    def find_by_order_id(self, order_id: OrderId) -> Optional[Payment]:
        pass
