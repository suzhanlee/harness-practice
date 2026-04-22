from typing import Dict, Optional

from ...domain.models.receipt import ReceiptRecord
from ...domain.repositories.receipt_repository import ReceiptRepository


class InMemoryReceiptRepository(ReceiptRepository):
    def __init__(self):
        self._store: Dict[str, ReceiptRecord] = {}

    def save(self, receipt: ReceiptRecord) -> None:
        self._store[receipt.order_id] = receipt

    def find_by_order_id(self, order_id: str) -> Optional[ReceiptRecord]:
        return self._store.get(order_id)
