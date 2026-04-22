from abc import ABC, abstractmethod
from typing import Optional

from ..models.split_payment import SplitPayment
from ..models.value_objects import SplitPaymentId, OrderId


class SplitPaymentRepository(ABC):

    @abstractmethod
    def save(self, split_payment: SplitPayment) -> None:
        pass

    @abstractmethod
    def find_by_id(self, split_payment_id: SplitPaymentId) -> Optional[SplitPayment]:
        pass

    @abstractmethod
    def find_by_order_id(self, order_id: OrderId) -> Optional[SplitPayment]:
        pass
