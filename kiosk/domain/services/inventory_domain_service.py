from ..models.order import Order
from ..repositories.menu_item_repository import MenuItemRepository


class InventoryDomainService:
    """재고 도메인 서비스: Order ↔ MenuItem cross-aggregate 재고 처리를 담당한다."""

    def validate_stock_for_order(self, order: Order, menu_repo: MenuItemRepository) -> None:
        for item in order.items:
            menu_item = menu_repo.find_by_id(item.menu_item_id)
            if menu_item is None:
                raise ValueError(f"메뉴 아이템을 찾을 수 없습니다: {item.menu_item_id}")
            if not menu_item.has_enough_stock(item.quantity):
                raise ValueError(
                    f"'{menu_item.name}' 재고가 부족합니다. "
                    f"현재 재고: {menu_item.stock.value}, 요청: {item.quantity}"
                )

    def consume_stock_for_order(self, order: Order, menu_repo: MenuItemRepository) -> None:
        self.validate_stock_for_order(order, menu_repo)
        for item in order.items:
            menu_item = menu_repo.find_by_id(item.menu_item_id)
            menu_item.decrease_stock(item.quantity)
            menu_repo.save(menu_item)
