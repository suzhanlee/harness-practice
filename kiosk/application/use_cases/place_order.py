from dataclasses import dataclass
from decimal import Decimal
from typing import List

from ...domain.models.order import Order, OrderItem
from ...domain.models.value_objects import MenuItemId
from ...domain.repositories.menu_item_repository import MenuItemRepository
from ...domain.repositories.order_repository import OrderRepository
from ...domain.services.order_domain_service import OrderDomainService


@dataclass
class OrderItemRequest:
    menu_item_id: str
    quantity: int


@dataclass
class PlaceOrderResult:
    order_id: str
    total_amount: Decimal
    currency: str
    item_count: int


class PlaceOrderUseCase:
    def __init__(
        self,
        menu_item_repo: MenuItemRepository,
        order_repo: OrderRepository,
        order_domain_service: OrderDomainService,
    ):
        self._menu_repo = menu_item_repo
        self._order_repo = order_repo
        self._domain_service = order_domain_service

    def execute(self, items: List[OrderItemRequest]) -> PlaceOrderResult:
        if not items:
            raise ValueError("주문 항목이 없습니다.")

        order = Order.create()

        for req in items:
            menu_item_id = MenuItemId.from_str(req.menu_item_id)
            menu_item = self._menu_repo.find_by_id(menu_item_id)
            if menu_item is None:
                raise ValueError(f"메뉴를 찾을 수 없습니다: {req.menu_item_id}")

            order_item = self._domain_service.create_order_item_from_menu(menu_item, req.quantity)
            order.add_item(order_item)

        order.confirm()
        self._order_repo.save(order)

        return PlaceOrderResult(
            order_id=str(order.id.value),
            total_amount=order.total_amount.amount,
            currency=order.total_amount.currency,
            item_count=order.item_count,
        )
