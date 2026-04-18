import pytest
from decimal import Decimal
from kiosk.domain.models.menu_item import MenuItem, MenuCategory
from kiosk.domain.models.value_objects import Money, DiscountRule


class TestMenuItemDiscount:
    def test_discounted_price_fixed(self):
        item = MenuItem.create("burger", Money(Decimal("10000")), MenuCategory.BURGER)
        rule = DiscountRule("fixed", Decimal("3000"), "product")
        discounted = item.get_discounted_price(rule)
        assert discounted.amount == Decimal("7000")

    def test_discounted_price_percentage(self):
        item = MenuItem.create("burger", Money(Decimal("10000")), MenuCategory.BURGER)
        rule = DiscountRule("percentage", Decimal("20"), "product")
        discounted = item.get_discounted_price(rule)
        assert discounted.amount == Decimal("8000")

    def test_discounted_price_fixed_no_negative(self):
        item = MenuItem.create("burger", Money(Decimal("1000")), MenuCategory.BURGER)
        rule = DiscountRule("fixed", Decimal("5000"), "product")
        discounted = item.get_discounted_price(rule)
        assert discounted.amount == Decimal("0")

    def test_discounted_price_preserves_currency(self):
        item = MenuItem.create("burger", Money(Decimal("10000"), "KRW"), MenuCategory.BURGER)
        rule = DiscountRule("percentage", Decimal("10"), "product")
        discounted = item.get_discounted_price(rule)
        assert discounted.currency == "KRW"
        assert discounted.amount == Decimal("9000")

    def test_discounted_price_invalid_type_raises(self):
        item = MenuItem.create("burger", Money(Decimal("10000")), MenuCategory.BURGER)
        rule = DiscountRule("fixed", Decimal("1000"), "product")
        # Manually set invalid type to test error handling
        object.__setattr__(rule, 'discount_type', 'invalid')
        with pytest.raises(ValueError, match="알 수 없는"):
            item.get_discounted_price(rule)
