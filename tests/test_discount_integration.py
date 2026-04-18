import pytest
from decimal import Decimal
from kiosk.domain.models.discount import Discount
from kiosk.domain.models.menu_item import MenuItem, MenuCategory
from kiosk.domain.models.order import Order, OrderItem
from kiosk.domain.models.value_objects import (
    DiscountId, CouponCode, DiscountRule, MenuItemId, Money
)
from kiosk.infrastructure.repositories.in_memory_discount_repository import InMemoryDiscountRepository
from kiosk.infrastructure.repositories.in_memory_menu_item_repository import InMemoryMenuItemRepository
from kiosk.infrastructure.repositories.in_memory_order_repository import InMemoryOrderRepository
from kiosk.application.use_cases.apply_coupon import ApplyCouponUseCase
from kiosk.application.use_cases.validate_discount import ValidateDiscountUseCase


class TestDiscountIntegration:
    @pytest.fixture
    def setup(self):
        menu_repo = InMemoryMenuItemRepository()
        order_repo = InMemoryOrderRepository()
        discount_repo = InMemoryDiscountRepository()

        burger = MenuItem.create("불고기버거", Money(Decimal("5000")), MenuCategory.BURGER)
        drink = MenuItem.create("콜라", Money(Decimal("2000")), MenuCategory.DRINK)
        menu_repo.save(burger)
        menu_repo.save(drink)

        return {
            "menu_repo": menu_repo,
            "order_repo": order_repo,
            "discount_repo": discount_repo,
            "burger": burger,
            "drink": drink,
        }

    def test_full_discount_flow_with_fixed_discount(self, setup):
        order = Order.create()
        setup["order_repo"].save(order)

        order.add_item(OrderItem(
            setup["burger"].id, setup["burger"].name,
            setup["burger"].price, 2
        ))
        order.add_item(OrderItem(
            setup["drink"].id, setup["drink"].name,
            setup["drink"].price, 1
        ))
        setup["order_repo"].save(order)

        discount = Discount(
            DiscountId.generate(),
            CouponCode("SUMMER5000"),
            DiscountRule("fixed", Decimal("5000"), "order"),
            is_active=True
        )
        setup["discount_repo"].save(discount)

        validate_uc = ValidateDiscountUseCase(setup["discount_repo"])
        validation_result = validate_uc.execute("SUMMER5000")
        assert validation_result.is_valid is True

        apply_uc = ApplyCouponUseCase(setup["order_repo"], setup["discount_repo"])
        apply_result = apply_uc.execute(str(order.id.value), "SUMMER5000")

        assert Decimal(apply_result.total_before) == Decimal("12000")
        assert Decimal(apply_result.total_after) == Decimal("7000")
        assert Decimal(apply_result.discount_amount) == Decimal("5000")

    def test_full_discount_flow_with_percentage_discount(self, setup):
        order = Order.create()
        setup["order_repo"].save(order)

        order.add_item(OrderItem(
            setup["burger"].id, setup["burger"].name,
            setup["burger"].price, 1
        ))
        setup["order_repo"].save(order)

        discount = Discount(
            DiscountId.generate(),
            CouponCode("WEEKEND20"),
            DiscountRule("percentage", Decimal("20"), "order"),
            is_active=True
        )
        setup["discount_repo"].save(discount)

        apply_uc = ApplyCouponUseCase(setup["order_repo"], setup["discount_repo"])
        apply_result = apply_uc.execute(str(order.id.value), "WEEKEND20")

        assert Decimal(apply_result.total_before) == Decimal("5000")
        assert Decimal(apply_result.total_after) == Decimal("4000")
        assert Decimal(apply_result.discount_amount) == Decimal("1000")

    def test_duplicate_coupon_prevention(self, setup):
        order = Order.create()
        setup["order_repo"].save(order)

        order.add_item(OrderItem(
            setup["burger"].id, setup["burger"].name,
            setup["burger"].price, 1
        ))
        setup["order_repo"].save(order)

        discount = Discount(
            DiscountId.generate(),
            CouponCode("NODUP"),
            DiscountRule("fixed", Decimal("1000"), "order"),
            is_active=True
        )
        setup["discount_repo"].save(discount)

        apply_uc = ApplyCouponUseCase(setup["order_repo"], setup["discount_repo"])
        apply_uc.execute(str(order.id.value), "NODUP")

        with pytest.raises(ValueError, match="이미 적용된"):
            apply_uc.execute(str(order.id.value), "NODUP")

    def test_multiple_discounts_accumulate(self, setup):
        order = Order.create()
        setup["order_repo"].save(order)

        order.add_item(OrderItem(
            setup["burger"].id, setup["burger"].name,
            setup["burger"].price, 1
        ))
        setup["order_repo"].save(order)

        discount1 = Discount(
            DiscountId.generate(),
            CouponCode("FIXED1000"),
            DiscountRule("fixed", Decimal("1000"), "order"),
            is_active=True
        )
        discount2 = Discount(
            DiscountId.generate(),
            CouponCode("PERCENT10"),
            DiscountRule("percentage", Decimal("10"), "order"),
            is_active=True
        )
        setup["discount_repo"].save(discount1)
        setup["discount_repo"].save(discount2)

        apply_uc = ApplyCouponUseCase(setup["order_repo"], setup["discount_repo"])
        apply_uc.execute(str(order.id.value), "FIXED1000")
        apply_uc.execute(str(order.id.value), "PERCENT10")

        updated_order = setup["order_repo"].find_by_id(order.id)
        assert Decimal(str(updated_order.get_total_after_discounts().amount)) == Decimal("3600")

    def test_inactive_discount_rejected(self, setup):
        order = Order.create()
        setup["order_repo"].save(order)

        order.add_item(OrderItem(
            setup["burger"].id, setup["burger"].name,
            setup["burger"].price, 1
        ))
        setup["order_repo"].save(order)

        discount = Discount(
            DiscountId.generate(),
            CouponCode("EXPIRED"),
            DiscountRule("fixed", Decimal("1000"), "order"),
            is_active=False
        )
        setup["discount_repo"].save(discount)

        apply_uc = ApplyCouponUseCase(setup["order_repo"], setup["discount_repo"])

        with pytest.raises(ValueError, match="사용 불가능"):
            apply_uc.execute(str(order.id.value), "EXPIRED")
