from typing import Dict, List, Optional

from ...domain.models.order import Order, OrderStatus
from ...domain.models.value_objects import OrderId
from ...domain.repositories.order_repository import OrderRepository


class InMemoryOrderRepository(OrderRepository):
    def __init__(self):
        self._store: Dict[OrderId, Order] = {}

    def save(self, order: Order) -> None:
        self._store[order.id] = order

    def find_by_id(self, order_id: OrderId) -> Optional[Order]:
        return self._store.get(order_id)

    def find_all(self) -> List[Order]:
        return list(self._store.values())

    def find_by_status(self, status: OrderStatus) -> List[Order]:
        return [o for o in self._store.values() if o.status == status]
