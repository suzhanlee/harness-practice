from ..models.order import Order, OrderItem
from ..models.menu_item import MenuItem
from ..models.value_objects import Money


class OrderDomainService:
    """주문 도메인 서비스: 여러 Aggregate에 걸친 도메인 로직을 처리한다."""

    def create_order_item_from_menu(self, menu_item: MenuItem, quantity: int) -> OrderItem:
        if not menu_item.available:
            raise ValueError(f"'{menu_item.name}'은 현재 주문할 수 없습니다.")
        if quantity <= 0:
            raise ValueError("수량은 1 이상이어야 합니다.")
        return OrderItem(
            menu_item_id=menu_item.id,
            name=menu_item.name,
            unit_price=menu_item.price,
            quantity=quantity,
        )

    def validate_order_for_payment(self, order: Order) -> None:
        from ..models.order import OrderStatus
        if order.status != OrderStatus.CONFIRMED:
            raise ValueError("확인된 주문만 결제할 수 있습니다.")
        if not order.items:
            raise ValueError("주문 항목이 없습니다.")
