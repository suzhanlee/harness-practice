import pytest
from decimal import Decimal

from kiosk.domain.models.menu_item import MenuItem, MenuCategory
from kiosk.domain.models.value_objects import Money


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

    def test_update_price(self, burger):
        new_price = Money(Decimal("6000"))
        burger.update_price(new_price)
        assert burger.price.amount == Decimal("6000")

    def test_update_price_zero_raises(self, burger):
        with pytest.raises(ValueError, match="0보다"):
            burger.update_price(Money(Decimal("0")))
