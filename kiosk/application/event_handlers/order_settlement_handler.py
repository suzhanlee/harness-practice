from __future__ import annotations

from datetime import datetime

from kiosk.domain.events.payment_events import OrderPaid
from kiosk.domain.models.receipt import ReceiptRecord
from kiosk.domain.repositories.order_repository import OrderRepository
from kiosk.domain.repositories.receipt_repository import ReceiptRepository


class OrderSettlementHandler:
    def __init__(
        self,
        order_repo: OrderRepository,
        receipt_repo: ReceiptRepository,
    ):
        self._order_repo = order_repo
        self._receipt_repo = receipt_repo

    def handle(self, event: OrderPaid) -> None:
        order = self._order_repo.find_by_id(event.order_id)
        if order is None:
            raise ValueError(f"Order not found: {event.order_id}")

        order.mark_paid()
        self._order_repo.save(order)

        receipt = ReceiptRecord.create(
            order_id=str(event.order_id.value),
            total_amount=str(event.total_amount.amount),
            paid_at=datetime.utcnow(),
        )
        self._receipt_repo.save(receipt)
