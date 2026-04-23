from abc import ABC, abstractmethod
from typing import Optional

from ..models.receipt import ReceiptRecord


class ReceiptRepository(ABC):

    @abstractmethod
    def save(self, receipt: ReceiptRecord) -> None:
        pass

    @abstractmethod
    def find_by_order_id(self, order_id: str) -> Optional[ReceiptRecord]:
        pass
