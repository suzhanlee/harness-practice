import pytest
from decimal import Decimal
from kiosk.domain.models.order import Order, OrderItem, OrderStatus
from kiosk.domain.models.value_objects import (
    MenuItemId, Money, FixedDiscountRule, PercentageDiscountRule
)


class TestApplyDiscount:
    def test_apply_fixed_discount(self):
        order = Order.create()
        item = OrderItem(MenuItemId.generate(), "burger", Money(Decimal("5000")), 1)
        order.add_item(item)

        rule = FixedDiscountRule(Money(Decimal("5000")))
        order.apply_discount(rule)

        assert len(order.get_discounts()) == 1
        assert order.get_total_after_discounts().amount == Decimal("0")

    def test_apply_percentage_discount(self):
        order = Order.create()
        item = OrderItem(MenuItemId.generate(), "burger", Money(Decimal("10000")), 1)
        order.add_item(item)

        rule = PercentageDiscountRule(Decimal("10"))
        order.apply_discount(rule)

        assert len(order.get_discounts()) == 1
        assert order.get_total_after_discounts().amount == Decimal("9000")

    def test_apply_multiple_discounts(self):
        order = Order.create()
        item = OrderItem(MenuItemId.generate(), "burger", Money(Decimal("10000")), 1)
        order.add_item(item)

        rule1 = FixedDiscountRule(Money(Decimal("1000")))
        rule2 = PercentageDiscountRule(Decimal("5"))
        order.apply_discount(rule1)
        order.apply_discount(rule2)

        assert len(order.get_discounts()) == 2
        total = order.get_total_after_discounts()
        assert total.amount == Decimal("8550")  # (10000 - 1000) * 0.95

    def test_apply_duplicate_rule_raises(self):
        order = Order.create()
        item = OrderItem(MenuItemId.generate(), "burger", Money(Decimal("5000")), 1)
        order.add_item(item)

        rule = FixedDiscountRule(Money(Decimal("1000")))
        order.apply_discount(rule)

        with pytest.raises(ValueError, match="이미 적용된"):
            order.apply_discount(rule)

    def test_apply_discount_on_non_pending_raises(self):
        order = Order.create()
        item = OrderItem(MenuItemId.generate(), "burger", Money(Decimal("5000")), 1)
        order.add_item(item)
        order.confirm()

        rule = FixedDiscountRule(Money(Decimal("1000")))

        with pytest.raises(ValueError, match="대기중 상태"):
            order.apply_discount(rule)

    def test_remove_discount(self):
        order = Order.create()
        item = OrderItem(MenuItemId.generate(), "burger", Money(Decimal("10000")), 1)
        order.add_item(item)

        rule = PercentageDiscountRule(Decimal("10"))
        order.apply_discount(rule)
        assert order.get_total_after_discounts().amount == Decimal("9000")

        order.remove_discount(rule)
        assert len(order.get_discounts()) == 0
        assert order.get_total_after_discounts().amount == Decimal("10000")

    def test_discount_total_never_negative(self):
        order = Order.create()
        item = OrderItem(MenuItemId.generate(), "burger", Money(Decimal("1000")), 1)
        order.add_item(item)

        rule = FixedDiscountRule(Money(Decimal("5000")))
        order.apply_discount(rule)

        assert order.get_total_after_discounts().amount == Decimal("0")
