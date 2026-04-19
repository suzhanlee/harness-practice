from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional
from kiosk.domain.models.order import Order, OrderItem, OrderStatus
from kiosk.domain.models.value_objects import OrderId, MenuItemId, Money
from kiosk.domain.repositories.order_repository import OrderRepository
from kiosk.domain.repositories.menu_item_repository import MenuItemRepository


@dataclass
class CartItemDTO:
    menu_item_id: str
    name: str
    unit_price: str
    quantity: int
    subtotal: str


@dataclass
class CartDTO:
    order_id: str
    items: List[CartItemDTO]
    total_amount: str
    item_count: int


class SetStockUseCase:
    def __init__(self, menu_repo: MenuItemRepository):
        self.menu_repo = menu_repo

    def execute(self, menu_item_id: str, stock: int) -> None:
        menu_item = self.menu_repo.find_by_id(MenuItemId.from_str(menu_item_id))
        if menu_item is None:
            raise ValueError(f"메뉴 아이템을 찾을 수 없습니다: {menu_item_id}")
        menu_item.set_stock(stock)
        self.menu_repo.save(menu_item)


class AddToCartUseCase:
    def __init__(self, order_repo: OrderRepository, menu_repo: Optional[MenuItemRepository] = None):
        self.order_repo = order_repo
        self.menu_repo = menu_repo

    def execute(self, order_id: str, menu_item_id: str, name: str, unit_price_amount: str, quantity: int) -> CartDTO:
        if self.menu_repo is not None:
            menu_item = self.menu_repo.find_by_id(MenuItemId.from_str(menu_item_id))
            if menu_item is not None and not menu_item.has_enough_stock(quantity):
                raise ValueError(f"'{name}' 재고가 부족합니다.")

        order = self._get_or_create_cart(order_id)

        item = OrderItem(
            menu_item_id=MenuItemId.from_str(menu_item_id),
            name=name,
            unit_price=Money(Decimal(unit_price_amount)),
            quantity=quantity
        )
        order.add_item(item)
        self.order_repo.save(order)

        return self._to_dto(order)

    def _get_or_create_cart(self, order_id: str) -> Order:
        if order_id:
            cart = self.order_repo.find_by_id(OrderId.from_str(order_id))
            if cart and cart.status == OrderStatus.PENDING:
                return cart
        return Order.create()

    def _to_dto(self, order: Order) -> CartDTO:
        return CartDTO(
            order_id=str(order.id.value),
            items=[
                CartItemDTO(
                    menu_item_id=str(item.menu_item_id.value),
                    name=item.name,
                    unit_price=str(item.unit_price.amount),
                    quantity=item.quantity,
                    subtotal=str(item.subtotal.amount)
                )
                for item in order.items
            ],
            total_amount=str(order.total_amount.amount),
            item_count=order.item_count
        )


class RemoveFromCartUseCase:
    def __init__(self, order_repo: OrderRepository):
        self.order_repo = order_repo

    def execute(self, order_id: str, menu_item_id: str) -> CartDTO:
        cart = self.order_repo.find_by_id(OrderId.from_str(order_id))
        if not cart or cart.status != OrderStatus.PENDING:
            raise ValueError(f"카트를 찾을 수 없습니다: {order_id}")

        cart.remove_item(MenuItemId.from_str(menu_item_id))
        self.order_repo.save(cart)

        return self._to_dto(cart)

    def _to_dto(self, order: Order) -> CartDTO:
        return CartDTO(
            order_id=str(order.id.value),
            items=[
                CartItemDTO(
                    menu_item_id=str(item.menu_item_id.value),
                    name=item.name,
                    unit_price=str(item.unit_price.amount),
                    quantity=item.quantity,
                    subtotal=str(item.subtotal.amount)
                )
                for item in order.items
            ],
            total_amount=str(order.total_amount.amount),
            item_count=order.item_count
        )


class UpdateQuantityUseCase:
    def __init__(self, order_repo: OrderRepository):
        self.order_repo = order_repo

    def execute(self, order_id: str, menu_item_id: str, new_quantity: int) -> CartDTO:
        cart = self.order_repo.find_by_id(OrderId.from_str(order_id))
        if not cart or cart.status != OrderStatus.PENDING:
            raise ValueError(f"카트를 찾을 수 없습니다: {order_id}")

        cart.update_item_quantity(MenuItemId.from_str(menu_item_id), new_quantity)
        self.order_repo.save(cart)

        return self._to_dto(cart)

    def _to_dto(self, order: Order) -> CartDTO:
        return CartDTO(
            order_id=str(order.id.value),
            items=[
                CartItemDTO(
                    menu_item_id=str(item.menu_item_id.value),
                    name=item.name,
                    unit_price=str(item.unit_price.amount),
                    quantity=item.quantity,
                    subtotal=str(item.subtotal.amount)
                )
                for item in order.items
            ],
            total_amount=str(order.total_amount.amount),
            item_count=order.item_count
        )


class ViewCartUseCase:
    def __init__(self, order_repo: OrderRepository):
        self.order_repo = order_repo

    def execute(self, order_id: str) -> CartDTO:
        cart = self.order_repo.find_by_id(OrderId.from_str(order_id))
        if not cart or cart.status != OrderStatus.PENDING:
            raise ValueError(f"카트를 찾을 수 없습니다: {order_id}")

        return self._to_dto(cart)

    def _to_dto(self, order: Order) -> CartDTO:
        return CartDTO(
            order_id=str(order.id.value),
            items=[
                CartItemDTO(
                    menu_item_id=str(item.menu_item_id.value),
                    name=item.name,
                    unit_price=str(item.unit_price.amount),
                    quantity=item.quantity,
                    subtotal=str(item.subtotal.amount)
                )
                for item in order.items
            ],
            total_amount=str(order.total_amount.amount),
            item_count=order.item_count
        )


class CheckoutUseCase:
    def __init__(self, order_repo: OrderRepository):
        self.order_repo = order_repo

    def execute(self, order_id: str) -> CartDTO:
        cart = self.order_repo.find_by_id(OrderId.from_str(order_id))
        if not cart or cart.status != OrderStatus.PENDING:
            raise ValueError(f"카트를 찾을 수 없습니다: {order_id}")

        cart.confirm()
        self.order_repo.save(cart)

        return self._to_dto(cart)

    def _to_dto(self, order: Order) -> CartDTO:
        return CartDTO(
            order_id=str(order.id.value),
            items=[
                CartItemDTO(
                    menu_item_id=str(item.menu_item_id.value),
                    name=item.name,
                    unit_price=str(item.unit_price.amount),
                    quantity=item.quantity,
                    subtotal=str(item.subtotal.amount)
                )
                for item in order.items
            ],
            total_amount=str(order.total_amount.amount),
            item_count=order.item_count
        )
