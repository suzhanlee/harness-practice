import pytest
import threading
from decimal import Decimal

from kiosk.domain.models.menu_item import MenuItem, MenuCategory
from kiosk.domain.models.order import Order, OrderStatus
from kiosk.domain.models.value_objects import Money
from kiosk.domain.services.order_domain_service import OrderDomainService
from kiosk.domain.services.inventory_domain_service import InventoryDomainService
from kiosk.infrastructure.repositories.in_memory_menu_item_repository import InMemoryMenuItemRepository


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


class TestInventoryDomainService:
    def setup_method(self):
        self.service = InventoryDomainService()
        self.menu_repo = InMemoryMenuItemRepository()

    def _make_menu_item(self, stock: int) -> MenuItem:
        item = MenuItem.create("테스트버거", Money(Decimal("5000")), MenuCategory.BURGER)
        item.set_stock(stock)
        self.menu_repo.save(item)
        return item

    def _make_order_with(self, menu_item: MenuItem, qty: int) -> Order:
        order_svc = OrderDomainService()
        order = Order.create()
        order_item = order_svc.create_order_item_from_menu(menu_item, qty)
        order.add_item(order_item)
        return order

    def test_consume_stock_decreases_stock(self):
        menu_item = self._make_menu_item(10)
        order = self._make_order_with(menu_item, 3)
        self.service.consume_stock_for_order(order, self.menu_repo)
        updated = self.menu_repo.find_by_id(menu_item.id)
        assert updated.stock.value == 7

    def test_consume_stock_marks_unavailable_when_depleted(self):
        menu_item = self._make_menu_item(2)
        order = self._make_order_with(menu_item, 2)
        self.service.consume_stock_for_order(order, self.menu_repo)
        updated = self.menu_repo.find_by_id(menu_item.id)
        assert updated.stock.value == 0
        assert updated.available is False

    def test_consume_stock_insufficient_raises(self):
        menu_item = self._make_menu_item(1)
        order = self._make_order_with(menu_item, 2)
        with pytest.raises(ValueError, match="재고가 부족"):
            self.service.consume_stock_for_order(order, self.menu_repo)

    def test_concurrent_orders_prevent_negative_stock(self):
        menu_item = self._make_menu_item(1)
        order_a = self._make_order_with(menu_item, 1)
        order_b = self._make_order_with(menu_item, 1)

        errors = []
        successes = []

        def attempt(order):
            try:
                self.service.consume_stock_for_order(order, self.menu_repo)
                successes.append(True)
            except ValueError:
                errors.append(True)

        t1 = threading.Thread(target=attempt, args=(order_a,))
        t2 = threading.Thread(target=attempt, args=(order_b,))
        t1.start(); t2.start()
        t1.join(); t2.join()

        final = self.menu_repo.find_by_id(menu_item.id)
        assert final.stock.value >= 0
        assert len(successes) <= 1
