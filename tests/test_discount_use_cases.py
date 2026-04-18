import pytest
from decimal import Decimal
from kiosk.application.use_cases.apply_coupon import ApplyCouponUseCase
from kiosk.application.use_cases.validate_discount import ValidateDiscountUseCase
from kiosk.infrastructure.repositories.in_memory_discount_repository import InMemoryDiscountRepository
from kiosk.infrastructure.repositories.in_memory_order_repository import InMemoryOrderRepository
from kiosk.domain.models.discount import Discount
from kiosk.domain.models.order import Order, OrderItem
from kiosk.domain.models.value_objects import (
    DiscountId, CouponCode, DiscountRule, MenuItemId, Money
)


class TestApplyCouponUseCase:
    @pytest.fixture
    def setup(self):
        discount_repo = InMemoryDiscountRepository()
        order_repo = InMemoryOrderRepository()

        discount = Discount(
            DiscountId.generate(),
            CouponCode("SAVE10"),
            DiscountRule("percentage", Decimal("10"), "order"),
            is_active=True
        )
        discount_repo.save(discount)

        order = Order.create()
        order.add_item(OrderItem(MenuItemId.generate(), "burger", Money(Decimal("10000")), 1))
        order_repo.save(order)

        return {
            "order_repo": order_repo,
            "discount_repo": discount_repo,
            "discount": discount,
            "order": order
        }

    def test_apply_coupon_success(self, setup):
        use_case = ApplyCouponUseCase(setup["order_repo"], setup["discount_repo"])
        result = use_case.execute(str(setup["order"].id.value), "SAVE10")

        assert result.coupon_code == "SAVE10"
        assert Decimal(result.total_before) == Decimal("10000")
        assert Decimal(result.total_after) == Decimal("9000")
        assert Decimal(result.discount_amount) == Decimal("1000")

    def test_apply_coupon_invalid_coupon(self, setup):
        use_case = ApplyCouponUseCase(setup["order_repo"], setup["discount_repo"])

        with pytest.raises(ValueError, match="유효한 쿠폰"):
            use_case.execute(str(setup["order"].id.value), "INVALID")

    def test_apply_coupon_order_not_found(self, setup):
        use_case = ApplyCouponUseCase(setup["order_repo"], setup["discount_repo"])

        with pytest.raises(ValueError, match="주문을 찾을 수"):
            use_case.execute("00000000-0000-0000-0000-000000000000", "SAVE10")


class TestValidateDiscountUseCase:
    @pytest.fixture
    def setup(self):
        discount_repo = InMemoryDiscountRepository()

        active_discount = Discount(
            DiscountId.generate(),
            CouponCode("VALID"),
            DiscountRule("percentage", Decimal("15"), "product"),
            is_active=True
        )
        inactive_discount = Discount(
            DiscountId.generate(),
            CouponCode("EXPIRED"),
            DiscountRule("fixed", Decimal("5000"), "order"),
            is_active=False
        )

        discount_repo.save(active_discount)
        discount_repo.save(inactive_discount)

        return {"discount_repo": discount_repo}

    def test_validate_active_coupon(self, setup):
        use_case = ValidateDiscountUseCase(setup["discount_repo"])
        result = use_case.execute("VALID")

        assert result.is_valid is True
        assert result.coupon_code == "VALID"
        assert result.discount_type == "percentage"
        assert result.discount_value == "15"
        assert result.applicable_target == "product"

    def test_validate_inactive_coupon(self, setup):
        use_case = ValidateDiscountUseCase(setup["discount_repo"])
        result = use_case.execute("EXPIRED")

        assert result.is_valid is False

    def test_validate_nonexistent_coupon(self, setup):
        use_case = ValidateDiscountUseCase(setup["discount_repo"])
        result = use_case.execute("NOTEXIST")

        assert result.is_valid is False
