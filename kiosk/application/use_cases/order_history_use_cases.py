from dataclasses import dataclass
from typing import List
from decimal import Decimal
from ...domain.models.value_objects import UserId, OrderId
from ...domain.repositories.order_repository import OrderRepository


@dataclass
class OrderSummaryDTO:
    order_id: str
    status: str
    total_amount: str
    item_count: int
    timestamp: str


@dataclass
class OrderHistorySnapshotDTO:
    status: str
    total_amount: str
    item_count: int
    timestamp: str


@dataclass
class OrderDetailDTO:
    order_id: str
    status: str
    total_amount: str
    item_count: int
    history: List[OrderHistorySnapshotDTO]


class GetOrderHistoryUseCase:
    def __init__(self, order_repo: OrderRepository):
        self.order_repo = order_repo

    def execute(self, user_id: str) -> List[OrderSummaryDTO]:
        orders = self.order_repo.find_by_user_id(UserId.from_str(user_id))
        result = []
        for order in orders:
            result.append(OrderSummaryDTO(
                order_id=str(order.id.value),
                status=order.status.value,
                total_amount=str(order.total_amount.amount),
                item_count=order.item_count,
                timestamp=str(order.history[-1].timestamp) if order.history else ""
            ))
        return result


class GetOrderDetailUseCase:
    def __init__(self, order_repo: OrderRepository):
        self.order_repo = order_repo

    def execute(self, order_id: str) -> OrderDetailDTO:
        order = self.order_repo.find_by_id(OrderId.from_str(order_id))
        if not order:
            raise ValueError(f"주문을 찾을 수 없습니다: {order_id}")

        history_snapshots = [
            OrderHistorySnapshotDTO(
                status=snapshot.status,
                total_amount=str(snapshot.total_amount.amount),
                item_count=snapshot.item_count,
                timestamp=str(snapshot.timestamp)
            )
            for snapshot in order.history
        ]

        return OrderDetailDTO(
            order_id=str(order.id.value),
            status=order.status.value,
            total_amount=str(order.total_amount.amount),
            item_count=order.item_count,
            history=history_snapshots
        )
