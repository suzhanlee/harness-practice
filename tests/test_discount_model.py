import pytest
from decimal import Decimal
from kiosk.domain.models.discount import Discount
from kiosk.domain.models.value_objects import DiscountId, CouponCode, DiscountRule


class TestDiscount:
    def test_create_discount(self):
        discount_id = DiscountId.generate()
        code = CouponCode("SAVE10")
        rule = DiscountRule("percentage", Decimal("10"), "product")
        discount = Discount(discount_id, code, rule, is_active=True)
        assert discount.id == discount_id
        assert discount.code == code
        assert discount.rule == rule
        assert discount.is_active is True

    def test_discount_inactive(self):
        discount_id = DiscountId.generate()
        code = CouponCode("EXPIRED")
        rule = DiscountRule("fixed", Decimal("5000"), "order")
        discount = Discount(discount_id, code, rule, is_active=False)
        assert discount.is_active is False

    def test_validate_coupon_active(self):
        discount = Discount(
            DiscountId.generate(),
            CouponCode("VALID"),
            DiscountRule("percentage", Decimal("10"), "product"),
            is_active=True
        )
        assert discount.validate_coupon() is True

    def test_validate_coupon_inactive(self):
        discount = Discount(
            DiscountId.generate(),
            CouponCode("INVALID"),
            DiscountRule("percentage", Decimal("10"), "product"),
            is_active=False
        )
        assert discount.validate_coupon() is False

    def test_discount_immutable(self):
        discount = Discount(
            DiscountId.generate(),
            CouponCode("TEST"),
            DiscountRule("fixed", Decimal("1000"), "product")
        )
        with pytest.raises(Exception):
            discount.is_active = False
