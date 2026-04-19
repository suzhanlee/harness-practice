import pytest
from decimal import Decimal

from kiosk.domain.models.menu_item import MenuItem, MenuCategory
from kiosk.domain.models.value_objects import Money, Stock


class TestMenuItem:
    def test_create_menu_item(self):
        item = MenuItem.create("불고기버거", Money(Decimal("5500")), MenuCategory.BURGER)
        assert item.name == "불고기버거"
        assert item.price.amount == Decimal("5500")
        assert item.category == MenuCategory.BURGER
        assert item.available is True

    def test_mark_unavailable(self, burger):
        burger.mark_unavailable()
        assert burger.available is False

    def test_mark_available(self, burger):
        burger.mark_unavailable()
        burger.mark_available()
        assert burger.available is True

    def test_change_price(self, burger):
        new_price = Money(Decimal("7000"))
        burger.change_price(new_price)
        assert burger.price.amount == Decimal("7000")

    def test_change_price_to_zero(self, burger):
        burger.change_price(Money(Decimal("0")))
        assert burger.price.amount == Decimal("0")

    def test_update_price(self, burger):
        new_price = Money(Decimal("6000"))
        burger.update_price(new_price)
        assert burger.price.amount == Decimal("6000")

    def test_update_price_zero_raises(self, burger):
        with pytest.raises(ValueError, match="0보다"):
            burger.update_price(Money(Decimal("0")))

    def test_default_stock_is_unlimited(self, burger):
        assert burger.stock.is_unlimited() is True

    def test_set_stock(self, burger):
        burger.set_stock(10)
        assert burger.stock.value == 10
        assert burger.stock.is_unlimited() is False

    def test_has_enough_stock(self, burger):
        burger.set_stock(5)
        assert burger.has_enough_stock(5) is True
        assert burger.has_enough_stock(6) is False

    def test_decrease_stock(self, burger):
        burger.set_stock(10)
        burger.decrease_stock(3)
        assert burger.stock.value == 7

    def test_decrease_stock_to_zero_marks_unavailable(self, burger):
        burger.set_stock(2)
        burger.decrease_stock(2)
        assert burger.stock.value == 0
        assert burger.available is False

    def test_decrease_stock_insufficient_raises(self, burger):
        burger.set_stock(1)
        with pytest.raises(ValueError, match="재고가 부족"):
            burger.decrease_stock(2)

    def test_restock_restores_availability(self, burger):
        burger.set_stock(1)
        burger.decrease_stock(1)
        assert burger.available is False
        burger.restock(5)
        assert burger.stock.value == 5  # 0 + 5
        assert burger.available is True
