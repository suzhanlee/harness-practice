import pytest
from decimal import Decimal

from kiosk.domain.models.order import Order, OrderItem, OrderStatus
from kiosk.domain.models.value_objects import Money, MenuItemId


def make_order_item(name="버거", price=Decimal("5000"), qty=1):
    return OrderItem(
        menu_item_id=MenuItemId.generate(),
        name=name,
        unit_price=Money(price),
        quantity=qty,
    )


class TestOrderItem:
    def test_subtotal(self):
        item = make_order_item(price=Decimal("3000"), qty=3)
        assert item.subtotal.amount == Decimal("9000")

    def test_zero_quantity_raises(self):
        with pytest.raises(ValueError, match="1 이상"):
            OrderItem(
                menu_item_id=MenuItemId.generate(),
                name="버거",
                unit_price=Money(Decimal("5000")),
                quantity=0,
            )

    def test_negative_quantity_raises(self):
        with pytest.raises(ValueError, match="1 이상"):
            OrderItem(
                menu_item_id=MenuItemId.generate(),
                name="버거",
                unit_price=Money(Decimal("5000")),
                quantity=-1,
            )


class TestOrder:
    def test_create_order(self):
        order = Order.create()
        assert order.status == OrderStatus.PENDING
        assert order.items == []

    def test_add_item(self):
        order = Order.create()
        item = make_order_item()
        order.add_item(item)
        assert len(order.items) == 1

    def test_add_duplicate_item_raises(self):
        order = Order.create()
        menu_item_id = MenuItemId.generate()
        item1 = OrderItem(menu_item_id=menu_item_id, name="버거", unit_price=Money(Decimal("5000")), quantity=1)
        item2 = OrderItem(menu_item_id=menu_item_id, name="버거", unit_price=Money(Decimal("5000")), quantity=2)
        order.add_item(item1)
        with pytest.raises(ValueError, match="이미 추가된"):
            order.add_item(item2)

    def test_remove_item(self):
        order = Order.create()
        item = make_order_item()
        order.add_item(item)
        order.remove_item(item.menu_item_id)
        assert len(order.items) == 0

    def test_total_amount(self):
        order = Order.create()
        order.add_item(make_order_item(price=Decimal("5000"), qty=1))
        order.add_item(make_order_item(price=Decimal("2000"), qty=2))
        assert order.total_amount.amount == Decimal("9000")

    def test_total_amount_empty(self):
        order = Order.create()
        assert order.total_amount.amount == Decimal("0")

    def test_item_count(self):
        order = Order.create()
        order.add_item(make_order_item(qty=2))
        order.add_item(make_order_item(qty=3))
        assert order.item_count == 5

    def test_confirm(self):
        order = Order.create()
        order.add_item(make_order_item())
        order.confirm()
        assert order.status == OrderStatus.CONFIRMED

    def test_confirm_empty_raises(self):
        order = Order.create()
        with pytest.raises(ValueError, match="항목"):
            order.confirm()

    def test_confirm_non_pending_raises(self):
        order = Order.create()
        order.add_item(make_order_item())
        order.confirm()
        with pytest.raises(ValueError, match="대기중"):
            order.confirm()

    def test_mark_paid(self):
        order = Order.create()
        order.add_item(make_order_item())
        order.confirm()
        order.mark_paid()
        assert order.status == OrderStatus.PAID

    def test_mark_paid_non_confirmed_raises(self):
        order = Order.create()
        with pytest.raises(ValueError, match="확인된"):
            order.mark_paid()

    def test_cancel_pending(self):
        order = Order.create()
        order.cancel()
        assert order.status == OrderStatus.CANCELLED

    def test_cancel_paid_raises(self):
        order = Order.create()
        order.add_item(make_order_item())
        order.confirm()
        order.mark_paid()
        with pytest.raises(ValueError, match="취소"):
            order.cancel()

    def test_add_item_to_confirmed_raises(self):
        order = Order.create()
        order.add_item(make_order_item())
        order.confirm()
        with pytest.raises(ValueError, match="대기중"):
            order.add_item(make_order_item())
