import pytest
from decimal import Decimal

from kiosk.domain.models.menu_item import MenuItem, MenuCategory
from kiosk.domain.models.order import Order, OrderStatus
from kiosk.domain.models.value_objects import Money
from kiosk.domain.services.order_domain_service import OrderDomainService


class TestOrderDomainService:
    def setup_method(self):
        self.service = OrderDomainService()

    def test_create_order_item_from_available_menu(self, burger):
        item = self.service.create_order_item_from_menu(burger, 2)
        assert item.name == burger.name
        assert item.unit_price == burger.price
        assert item.quantity == 2

    def test_create_order_item_unavailable_raises(self, burger):
        burger.mark_unavailable()
        with pytest.raises(ValueError, match="주문할 수 없"):
            self.service.create_order_item_from_menu(burger, 1)

    def test_create_order_item_zero_qty_raises(self, burger):
        with pytest.raises(ValueError, match="1 이상"):
            self.service.create_order_item_from_menu(burger, 0)

    def test_validate_order_for_payment_confirmed_ok(self, burger):
        order = Order.create()
        item = self.service.create_order_item_from_menu(burger, 1)
        order.add_item(item)
        order.confirm()
        self.service.validate_order_for_payment(order)  # should not raise

    def test_validate_order_for_payment_pending_raises(self, burger):
        order = Order.create()
        item = self.service.create_order_item_from_menu(burger, 1)
        order.add_item(item)
        with pytest.raises(ValueError, match="확인된"):
            self.service.validate_order_for_payment(order)
