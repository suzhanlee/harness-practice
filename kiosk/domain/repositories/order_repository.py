from abc import ABC, abstractmethod
from typing import List, Optional
from ..models.order import Order, OrderStatus
from ..models.value_objects import OrderId, UserId, OrderStateSnapshot


class OrderRepository(ABC):

    @abstractmethod
    def save(self, order: Order) -> None:
        pass

    @abstractmethod
    def find_by_id(self, order_id: OrderId) -> Optional[Order]:
        pass

    @abstractmethod
    def find_all(self) -> List[Order]:
        pass

    @abstractmethod
    def find_by_status(self, status: OrderStatus) -> List[Order]:
        pass

    @abstractmethod
    def find_by_user_id(self, user_id: UserId) -> List[Order]:
        pass

    @abstractmethod
    def get_order_history(self, order_id: OrderId) -> List[OrderStateSnapshot]:
        pass
