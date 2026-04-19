from __future__ import annotations
from dataclasses import dataclass

from kiosk.domain.models.order import OrderStatus
from kiosk.domain.models.value_objects import MenuItemId
from kiosk.domain.repositories.menu_item_repository import MenuItemRepository
from kiosk.domain.repositories.order_repository import OrderRepository


@dataclass(frozen=True)
class MarkUnavailableDTO:
    id: str
    name: str
    available: bool
    affected_orders: int


class MarkMenuUnavailableUseCase:
    def __init__(self, menu_repo: MenuItemRepository, order_repo: OrderRepository):
        self.menu_repo = menu_repo
        self.order_repo = order_repo

    def execute(self, menu_item_id: str) -> MarkUnavailableDTO:
        mid = MenuItemId.from_str(menu_item_id)
        item = self.menu_repo.find_by_id(mid)
        if not item:
            raise ValueError(f"메뉴를 찾을 수 없습니다: {menu_item_id}")

        item.mark_unavailable()
        self.menu_repo.save(item)

        pending_orders = self.order_repo.find_by_status(OrderStatus.PENDING)
        affected = 0
        for order in pending_orders:
            for order_item in order.items:
                if order_item.menu_item_id == mid:
                    order_item.is_available = False
                    self.order_repo.save(order)
                    affected += 1
                    break

        return MarkUnavailableDTO(
            id=str(item.id.value),
            name=item.name,
            available=item.available,
            affected_orders=affected,
        )
