from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from kiosk.domain.models.order import Order, OrderStatus
from kiosk.domain.repositories.order_repository import OrderRepository


@dataclass(frozen=True)
class OrderSummaryDTO:
    id: str
    status: str
    total_amount: Decimal
    currency: str
    item_count: int


def _to_dto(order: Order) -> OrderSummaryDTO:
    return OrderSummaryDTO(
        id=str(order.id.value),
        status=order.status.value,
        total_amount=order.total_amount.amount,
        currency=order.total_amount.currency,
        item_count=order.item_count,
    )


class QueryOrdersUseCase:
    def __init__(self, order_repo: OrderRepository):
        self.order_repo = order_repo

    def execute(self, status_filter: Optional[str] = None) -> List[OrderSummaryDTO]:
        if status_filter is not None:
            status = OrderStatus(status_filter)
            orders = self.order_repo.find_by_status(status)
        else:
            orders = self.order_repo.find_all()
        return [_to_dto(o) for o in orders]
