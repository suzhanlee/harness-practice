import pytest
from decimal import Decimal
from kiosk.domain.models.order import Order, OrderItem, OrderStatus
from kiosk.domain.models.menu_item import MenuItem
from kiosk.domain.models.discount import Discount
from kiosk.domain.models.value_objects import (
    MenuItemId, Money, CouponCode, DiscountRule, DiscountId
)


class TestApplyDiscount:
    def test_apply_fixed_discount(self):
        order = Order.create()
        item = OrderItem(MenuItemId.generate(), "burger", Money(Decimal("5000")), 1)
        order.add_item(item)

        discount = Discount(
            DiscountId.generate(),
            CouponCode("SAVE5000"),
            DiscountRule("fixed", Decimal("5000"), "order")
        )
        order.apply_discount(discount)

        assert len(order.get_discounts()) == 1
        assert order.get_total_after_discounts().amount == Decimal("0")

    def test_apply_percentage_discount(self):
        order = Order.create()
        item = OrderItem(MenuItemId.generate(), "burger", Money(Decimal("10000")), 1)
        order.add_item(item)

        discount = Discount(
            DiscountId.generate(),
            CouponCode("SAVE10"),
            DiscountRule("percentage", Decimal("10"), "order")
        )
        order.apply_discount(discount)

        assert len(order.get_discounts()) == 1
        assert order.get_total_after_discounts().amount == Decimal("9000")

    def test_apply_multiple_discounts(self):
        order = Order.create()
        item = OrderItem(MenuItemId.generate(), "burger", Money(Decimal("10000")), 1)
        order.add_item(item)

        discount1 = Discount(
            DiscountId.generate(),
            CouponCode("FIXED1000"),
            DiscountRule("fixed", Decimal("1000"), "order")
        )
        discount2 = Discount(
            DiscountId.generate(),
            CouponCode("PERCENT5"),
            DiscountRule("percentage", Decimal("5"), "order")
        )
        order.apply_discount(discount1)
        order.apply_discount(discount2)

        assert len(order.get_discounts()) == 2
        total = order.get_total_after_discounts()
        assert total.amount == Decimal("8550")  # (10000 - 1000) * 0.95

    def test_apply_duplicate_coupon_raises(self):
        order = Order.create()
        item = OrderItem(MenuItemId.generate(), "burger", Money(Decimal("5000")), 1)
        order.add_item(item)

        discount = Discount(
            DiscountId.generate(),
            CouponCode("DUP"),
            DiscountRule("fixed", Decimal("1000"), "order")
        )
        order.apply_discount(discount)

        with pytest.raises(ValueError, match="이미 적용된"):
            order.apply_discount(discount)

    def test_apply_discount_on_non_pending_raises(self):
        order = Order.create()
        item = OrderItem(MenuItemId.generate(), "burger", Money(Decimal("5000")), 1)
        order.add_item(item)
        order.confirm()

        discount = Discount(
            DiscountId.generate(),
            CouponCode("EXPIRED"),
            DiscountRule("fixed", Decimal("1000"), "order")
        )

        with pytest.raises(ValueError, match="대기중 상태"):
            order.apply_discount(discount)

    def test_remove_discount(self):
        order = Order.create()
        item = OrderItem(MenuItemId.generate(), "burger", Money(Decimal("10000")), 1)
        order.add_item(item)

        discount = Discount(
            DiscountId.generate(),
            CouponCode("REMOVE"),
            DiscountRule("percentage", Decimal("10"), "order")
        )
        order.apply_discount(discount)
        assert order.get_total_after_discounts().amount == Decimal("9000")

        order.remove_discount(discount.id)
        assert len(order.get_discounts()) == 0
        assert order.get_total_after_discounts().amount == Decimal("10000")

    def test_discount_total_never_negative(self):
        order = Order.create()
        item = OrderItem(MenuItemId.generate(), "burger", Money(Decimal("1000")), 1)
        order.add_item(item)

        discount = Discount(
            DiscountId.generate(),
            CouponCode("LARGE"),
            DiscountRule("fixed", Decimal("5000"), "order")
        )
        order.apply_discount(discount)

        assert order.get_total_after_discounts().amount == Decimal("0")
