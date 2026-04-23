import pytest
from decimal import Decimal

from kiosk.application.use_cases.get_menu import GetMenuUseCase
from kiosk.application.use_cases.place_order import PlaceOrderUseCase, OrderItemRequest
from kiosk.application.use_cases.process_payment import ProcessPaymentUseCase
from kiosk.application.use_cases.cart_use_cases import SetStockUseCase, AddToCartUseCase
from kiosk.application.use_cases.create_split_payment import CreateSplitPaymentUseCase
from kiosk.application.use_cases.add_payment_attempt import AddPaymentAttemptUseCase
from kiosk.application.use_cases.issue_coupon import IssueCouponUseCase, CouponDTO
from kiosk.application.use_cases.apply_coupon import ApplyCouponUseCase
from kiosk.domain.models.coupon import CouponExpiredError, CouponUsageLimitExceededError, CouponAlreadyUsedError
from kiosk.domain.models.payment import PaymentStatus
from kiosk.domain.services.inventory_domain_service import InventoryDomainService
from kiosk.infrastructure.repositories.in_memory_menu_item_repository import InMemoryMenuItemRepository
from kiosk.infrastructure.repositories.in_memory_split_payment_repository import InMemorySplitPaymentRepository
from kiosk.infrastructure.repositories.in_memory_coupon_repository import InMemoryCouponRepository


class TestGetMenuUseCase:
    def test_get_all_available(self, seeded_menu_repo):
        use_case = GetMenuUseCase(seeded_menu_repo)
        items = use_case.execute(available_only=True)
        assert len(items) == 6
        assert all(item.available for item in items)

    def test_returns_dto(self, seeded_menu_repo):
        use_case = GetMenuUseCase(seeded_menu_repo)
        items = use_case.execute()
        item = items[0]
        assert hasattr(item, "id")
        assert hasattr(item, "name")
        assert hasattr(item, "price")
        assert hasattr(item, "category")


class TestPlaceOrderUseCase:
    def test_place_order_success(self, seeded_menu_repo, order_repo, domain_service):
        menu_items = seeded_menu_repo.find_available()
        use_case = PlaceOrderUseCase(seeded_menu_repo, order_repo, domain_service)

        requests = [
            OrderItemRequest(menu_item_id=str(menu_items[0].id.value), quantity=1),
            OrderItemRequest(menu_item_id=str(menu_items[1].id.value), quantity=2),
        ]
        result = use_case.execute(requests)

        assert result.order_id is not None
        assert result.item_count == 3
        assert result.total_amount > Decimal("0")

    def test_place_order_empty_raises(self, seeded_menu_repo, order_repo, domain_service):
        use_case = PlaceOrderUseCase(seeded_menu_repo, order_repo, domain_service)
        with pytest.raises(ValueError, match="항목"):
            use_case.execute([])

    def test_place_order_invalid_menu_item_raises(self, seeded_menu_repo, order_repo, domain_service):
        import uuid
        use_case = PlaceOrderUseCase(seeded_menu_repo, order_repo, domain_service)
        with pytest.raises(ValueError, match="메뉴"):
            use_case.execute([OrderItemRequest(menu_item_id=str(uuid.uuid4()), quantity=1)])

    def test_place_order_unavailable_item_raises(self, seeded_menu_repo, order_repo, domain_service):
        menu_items = seeded_menu_repo.find_available()
        menu_items[0].mark_unavailable()
        use_case = PlaceOrderUseCase(seeded_menu_repo, order_repo, domain_service)
        with pytest.raises(ValueError, match="주문할 수 없"):
            use_case.execute([OrderItemRequest(menu_item_id=str(menu_items[0].id.value), quantity=1)])

    def test_placed_order_saved_in_repo(self, seeded_menu_repo, order_repo, domain_service):
        menu_items = seeded_menu_repo.find_available()
        use_case = PlaceOrderUseCase(seeded_menu_repo, order_repo, domain_service)
        result = use_case.execute([OrderItemRequest(menu_item_id=str(menu_items[0].id.value), quantity=1)])

        from kiosk.domain.models.value_objects import OrderId
        saved = order_repo.find_by_id(OrderId.from_str(result.order_id))
        assert saved is not None


class TestProcessPaymentUseCase:
    def _place_order(self, seeded_menu_repo, order_repo, domain_service):
        menu_items = seeded_menu_repo.find_available()
        place = PlaceOrderUseCase(seeded_menu_repo, order_repo, domain_service)
        return place.execute([OrderItemRequest(menu_item_id=str(menu_items[0].id.value), quantity=1)])

    def test_process_payment_card(self, seeded_menu_repo, order_repo, payment_repo, domain_service):
        order_result = self._place_order(seeded_menu_repo, order_repo, domain_service)
        use_case = ProcessPaymentUseCase(order_repo, payment_repo, domain_service)

        result = use_case.execute(order_result.order_id, "카드")

        assert result.success is True
        assert result.method == "카드"
        assert result.payment_id is not None

    def test_process_payment_cash(self, seeded_menu_repo, order_repo, payment_repo, domain_service):
        order_result = self._place_order(seeded_menu_repo, order_repo, domain_service)
        use_case = ProcessPaymentUseCase(order_repo, payment_repo, domain_service)

        result = use_case.execute(order_result.order_id, "현금")
        assert result.method == "현금"

    def test_process_payment_invalid_order_raises(self, order_repo, payment_repo, domain_service):
        import uuid
        use_case = ProcessPaymentUseCase(order_repo, payment_repo, domain_service)
        with pytest.raises(ValueError, match="주문"):
            use_case.execute(str(uuid.uuid4()), "카드")

    def test_payment_saved_in_repo(self, seeded_menu_repo, order_repo, payment_repo, domain_service):
        order_result = self._place_order(seeded_menu_repo, order_repo, domain_service)
        use_case = ProcessPaymentUseCase(order_repo, payment_repo, domain_service)
        pay_result = use_case.execute(order_result.order_id, "카드")

        from kiosk.domain.models.value_objects import OrderId
        saved = payment_repo.find_by_order_id(OrderId.from_str(order_result.order_id))
        assert saved is not None
        assert saved.status == PaymentStatus.COMPLETED

    def test_order_status_paid_after_payment(self, seeded_menu_repo, order_repo, payment_repo, domain_service):
        order_result = self._place_order(seeded_menu_repo, order_repo, domain_service)
        use_case = ProcessPaymentUseCase(order_repo, payment_repo, domain_service)
        use_case.execute(order_result.order_id, "카드")

        from kiosk.domain.models.value_objects import OrderId
        from kiosk.domain.models.order import OrderStatus
        order = order_repo.find_by_id(OrderId.from_str(order_result.order_id))
        assert order.status == OrderStatus.PAID


class TestSetStockUseCase:
    def test_set_stock(self, seeded_menu_repo):
        menu_items = seeded_menu_repo.find_available()
        target = menu_items[0]
        use_case = SetStockUseCase(seeded_menu_repo)
        use_case.execute(str(target.id.value), 20)
        updated = seeded_menu_repo.find_by_id(target.id)
        assert updated.stock.value == 20

    def test_set_stock_invalid_id_raises(self, seeded_menu_repo):
        import uuid
        use_case = SetStockUseCase(seeded_menu_repo)
        with pytest.raises(ValueError, match="찾을 수 없"):
            use_case.execute(str(uuid.uuid4()), 10)


class TestAddToCartStockCheck:
    def test_add_to_cart_with_sufficient_stock(self, order_repo, seeded_menu_repo):
        menu_item = seeded_menu_repo.find_available()[0]
        menu_item.set_stock(5)
        seeded_menu_repo.save(menu_item)
        use_case = AddToCartUseCase(order_repo, menu_repo=seeded_menu_repo)
        result = use_case.execute("", str(menu_item.id.value), menu_item.name, str(menu_item.price.amount), 3)
        assert result.item_count == 3

    def test_add_to_cart_insufficient_stock_raises(self, order_repo, seeded_menu_repo):
        menu_item = seeded_menu_repo.find_available()[0]
        menu_item.set_stock(1)
        seeded_menu_repo.save(menu_item)
        use_case = AddToCartUseCase(order_repo, menu_repo=seeded_menu_repo)
        with pytest.raises(ValueError, match="재고가 부족"):
            use_case.execute("", str(menu_item.id.value), menu_item.name, str(menu_item.price.amount), 2)


class TestProcessPaymentWithInventory:
    def _place_order(self, seeded_menu_repo, order_repo, domain_service, menu_item, qty):
        place = PlaceOrderUseCase(seeded_menu_repo, order_repo, domain_service)
        from kiosk.application.use_cases.place_order import OrderItemRequest
        return place.execute([OrderItemRequest(menu_item_id=str(menu_item.id.value), quantity=qty)])

    def test_payment_decreases_stock(self, seeded_menu_repo, order_repo, payment_repo, domain_service):
        menu_item = seeded_menu_repo.find_available()[0]
        menu_item.set_stock(10)
        seeded_menu_repo.save(menu_item)

        order_result = self._place_order(seeded_menu_repo, order_repo, domain_service, menu_item, 3)
        use_case = ProcessPaymentUseCase(
            order_repo, payment_repo, domain_service,
            inventory_service=InventoryDomainService(),
            menu_repo=seeded_menu_repo,
        )
        use_case.execute(order_result.order_id, "카드")
        updated = seeded_menu_repo.find_by_id(menu_item.id)
        assert updated.stock.value == 7

    def test_payment_fails_when_stock_depleted(self, seeded_menu_repo, order_repo, payment_repo, domain_service):
        menu_item = seeded_menu_repo.find_available()[0]
        menu_item.set_stock(1)
        seeded_menu_repo.save(menu_item)

        order_result = self._place_order(seeded_menu_repo, order_repo, domain_service, menu_item, 1)
        # 재고를 먼저 소진
        menu_item.decrease_stock(1)
        seeded_menu_repo.save(menu_item)

        use_case = ProcessPaymentUseCase(
            order_repo, payment_repo, domain_service,
            inventory_service=InventoryDomainService(),
            menu_repo=seeded_menu_repo,
        )
        with pytest.raises(ValueError, match="재고가 부족"):
            use_case.execute(order_result.order_id, "카드")


class TestCreateSplitPaymentUseCase:
    def _place_and_confirm_order(self, seeded_menu_repo, order_repo, domain_service):
        menu_items = seeded_menu_repo.find_available()
        place = PlaceOrderUseCase(seeded_menu_repo, order_repo, domain_service)
        order_result = place.execute([OrderItemRequest(menu_item_id=str(menu_items[0].id.value), quantity=1)])
        return order_result

    def test_create_split_payment_returns_dto(self, seeded_menu_repo, order_repo, domain_service):
        order_result = self._place_and_confirm_order(seeded_menu_repo, order_repo, domain_service)
        split_payment_repo = InMemorySplitPaymentRepository()
        use_case = CreateSplitPaymentUseCase(order_repo, split_payment_repo)

        result = use_case.execute(order_result.order_id)

        assert result.split_payment_id is not None
        assert result.order_id == order_result.order_id
        assert result.is_fully_paid is False

    def test_create_split_payment_target_amount_matches_order_total(self, seeded_menu_repo, order_repo, domain_service):
        order_result = self._place_and_confirm_order(seeded_menu_repo, order_repo, domain_service)
        split_payment_repo = InMemorySplitPaymentRepository()
        use_case = CreateSplitPaymentUseCase(order_repo, split_payment_repo)

        result = use_case.execute(order_result.order_id)

        assert Decimal(result.target_amount) == order_result.total_amount

    def test_create_split_payment_saved_in_repo(self, seeded_menu_repo, order_repo, domain_service):
        order_result = self._place_and_confirm_order(seeded_menu_repo, order_repo, domain_service)
        split_payment_repo = InMemorySplitPaymentRepository()
        use_case = CreateSplitPaymentUseCase(order_repo, split_payment_repo)

        result = use_case.execute(order_result.order_id)

        from kiosk.domain.models.value_objects import SplitPaymentId
        saved = split_payment_repo.find_by_id(SplitPaymentId.from_str(result.split_payment_id))
        assert saved is not None

    def test_create_split_payment_raises_if_order_not_confirmed(self, seeded_menu_repo, order_repo, domain_service):
        """PENDING 상태 주문에는 분할 결제 생성 불가"""
        from kiosk.domain.models.order import Order
        order = Order.create()
        from kiosk.domain.models.order import OrderItem
        from kiosk.domain.models.value_objects import MenuItemId, Money
        order.add_item(OrderItem(MenuItemId.generate(), "테스트", Money(Decimal("1000")), 1))
        order_repo.save(order)

        split_payment_repo = InMemorySplitPaymentRepository()
        use_case = CreateSplitPaymentUseCase(order_repo, split_payment_repo)

        with pytest.raises(ValueError, match="확인된 주문"):
            use_case.execute(str(order.id.value))

    def test_create_split_payment_raises_if_order_not_found(self, order_repo):
        import uuid
        split_payment_repo = InMemorySplitPaymentRepository()
        use_case = CreateSplitPaymentUseCase(order_repo, split_payment_repo)

        with pytest.raises(ValueError, match="주문"):
            use_case.execute(str(uuid.uuid4()))


class TestAddPaymentAttemptUseCase:
    def _create_split_payment(self, seeded_menu_repo, order_repo, domain_service):
        menu_items = seeded_menu_repo.find_available()
        place = PlaceOrderUseCase(seeded_menu_repo, order_repo, domain_service)
        order_result = place.execute([OrderItemRequest(menu_item_id=str(menu_items[0].id.value), quantity=1)])

        split_payment_repo = InMemorySplitPaymentRepository()
        create_uc = CreateSplitPaymentUseCase(order_repo, split_payment_repo)
        split_payment_result = create_uc.execute(order_result.order_id)
        return split_payment_result, split_payment_repo, order_result

    def test_add_split_payment_attempt_returns_result(self, seeded_menu_repo, order_repo, domain_service):
        split_payment_result, split_payment_repo, order_result = self._create_split_payment(
            seeded_menu_repo, order_repo, domain_service
        )
        use_case = AddPaymentAttemptUseCase(split_payment_repo)
        partial_amount = str(Decimal(split_payment_result.target_amount) / 2)

        result = use_case.execute(split_payment_result.split_payment_id, partial_amount)

        assert result.attempt_id is not None
        assert result.authorized_amount == partial_amount
        assert result.is_fully_paid is False

    def test_add_split_payment_attempt_remaining_amount_decreases(self, seeded_menu_repo, order_repo, domain_service):
        split_payment_result, split_payment_repo, order_result = self._create_split_payment(
            seeded_menu_repo, order_repo, domain_service
        )
        use_case = AddPaymentAttemptUseCase(split_payment_repo)
        target = Decimal(split_payment_result.target_amount)
        partial = target / 2

        result = use_case.execute(split_payment_result.split_payment_id, str(partial))

        assert Decimal(result.remaining_amount) == target - partial

    def test_add_split_payment_attempt_fully_paid_when_complete(self, seeded_menu_repo, order_repo, domain_service):
        split_payment_result, split_payment_repo, order_result = self._create_split_payment(
            seeded_menu_repo, order_repo, domain_service
        )
        use_case = AddPaymentAttemptUseCase(split_payment_repo)
        target = Decimal(split_payment_result.target_amount)

        result = use_case.execute(split_payment_result.split_payment_id, str(target))

        assert result.is_fully_paid is True
        assert Decimal(result.remaining_amount) == Decimal("0")

    def test_add_split_payment_attempt_raises_if_not_found(self):
        import uuid
        split_payment_repo = InMemorySplitPaymentRepository()
        use_case = AddPaymentAttemptUseCase(split_payment_repo)

        with pytest.raises(ValueError, match="분할 결제"):
            use_case.execute(str(uuid.uuid4()), "1000")


class TestIssueCouponUseCase:
    """IssueCouponUseCase 단위 테스트 — -k coupon 에 의해 선택됩니다."""

    @pytest.fixture
    def coupon_repo(self):
        return InMemoryCouponRepository()

    def test_issue_coupon_fixed_returns_dto(self, coupon_repo):
        use_case = IssueCouponUseCase(coupon_repo)
        result = use_case.execute(
            code="FIXED1000",
            discount_type="fixed",
            discount_value="1000",
            max_usage=5,
            expires_at="2099-12-31T23:59:59",
        )

        assert isinstance(result, CouponDTO)
        assert result.code == "FIXED1000"
        assert result.discount_type == "fixed"
        assert result.discount_value == "1000"
        assert result.max_usage == 5
        assert result.coupon_id is not None

    def test_issue_coupon_percentage_returns_dto(self, coupon_repo):
        use_case = IssueCouponUseCase(coupon_repo)
        result = use_case.execute(
            code="PCT10",
            discount_type="percentage",
            discount_value="10",
            max_usage=3,
            expires_at="2099-06-30T00:00:00",
        )

        assert result.discount_type == "percentage"
        assert result.discount_value == "10"
        assert result.max_usage == 3

    def test_issue_coupon_saved_in_repo(self, coupon_repo):
        use_case = IssueCouponUseCase(coupon_repo)
        result = use_case.execute(
            code="SAVEME",
            discount_type="fixed",
            discount_value="500",
            max_usage=1,
            expires_at="2099-01-01T00:00:00",
        )

        from kiosk.domain.models.value_objects import CouponId
        saved = coupon_repo.find_by_id(CouponId.from_str(result.coupon_id))
        assert saved is not None
        assert saved.code.value == "SAVEME"

    def test_issue_coupon_invalid_type_raises(self, coupon_repo):
        use_case = IssueCouponUseCase(coupon_repo)
        with pytest.raises(ValueError, match="discount_type"):
            use_case.execute(
                code="BAD",
                discount_type="unknown",
                discount_value="100",
                max_usage=1,
                expires_at="2099-01-01T00:00:00",
            )


class TestApplyCouponUseCase:
    """ApplyCouponUseCase 단위 테스트 — -k coupon 에 의해 선택됩니다."""

    FUTURE = "2099-12-31T23:59:59"
    NOW_VALID = "2026-04-22T10:00:00"
    NOW_EXPIRED = "2100-01-01T00:00:00"

    @pytest.fixture
    def coupon_repo(self):
        return InMemoryCouponRepository()

    def _issue(self, coupon_repo, code="TEST500", discount_type="fixed",
               discount_value="500", max_usage=3, expires_at=None):
        if expires_at is None:
            expires_at = self.FUTURE
        uc = IssueCouponUseCase(coupon_repo)
        return uc.execute(code, discount_type, discount_value, max_usage, expires_at)

    def test_apply_coupon_returns_dto(self, coupon_repo):
        import uuid
        self._issue(coupon_repo)
        use_case = ApplyCouponUseCase(coupon_repo)
        result = use_case.execute(
            order_id=str(uuid.uuid4()),
            coupon_code="TEST500",
            now=self.NOW_VALID,
        )

        assert isinstance(result, CouponDTO)
        assert result.code == "TEST500"
        assert result.discount_type == "fixed"
        assert result.discount_value == "500"

    def test_apply_coupon_not_found_raises(self, coupon_repo):
        import uuid
        use_case = ApplyCouponUseCase(coupon_repo)
        with pytest.raises(ValueError, match="쿠폰을 찾을 수 없습니다"):
            use_case.execute(str(uuid.uuid4()), "NOTEXIST", self.NOW_VALID)

    def test_apply_coupon_expired_raises(self, coupon_repo):
        import uuid
        self._issue(coupon_repo, code="EXPRD", expires_at="2020-01-01T00:00:00")
        use_case = ApplyCouponUseCase(coupon_repo)
        with pytest.raises(CouponExpiredError):
            use_case.execute(str(uuid.uuid4()), "EXPRD", self.NOW_VALID)

    def test_apply_coupon_usage_limit_exceeded_raises(self, coupon_repo):
        import uuid
        self._issue(coupon_repo, code="ONCE", max_usage=1)
        use_case = ApplyCouponUseCase(coupon_repo)
        # 첫 번째 사용 — 성공
        use_case.execute(str(uuid.uuid4()), "ONCE", self.NOW_VALID)
        # 두 번째 사용 — 초과
        with pytest.raises(CouponUsageLimitExceededError):
            use_case.execute(str(uuid.uuid4()), "ONCE", self.NOW_VALID)

    def test_apply_coupon_already_used_on_same_order_raises(self, coupon_repo):
        import uuid
        self._issue(coupon_repo, code="DUPORD", max_usage=5)
        order_id = str(uuid.uuid4())
        use_case = ApplyCouponUseCase(coupon_repo)
        use_case.execute(order_id, "DUPORD", self.NOW_VALID)
        with pytest.raises(CouponAlreadyUsedError):
            use_case.execute(order_id, "DUPORD", self.NOW_VALID)

    def test_apply_coupon_saves_state(self, coupon_repo):
        """redeem 후 coupon_repo.save() 가 호출돼 usage_count 가 영속됩니다."""
        import uuid
        dto = self._issue(coupon_repo, code="PERSIST", max_usage=2)
        use_case = ApplyCouponUseCase(coupon_repo)
        use_case.execute(str(uuid.uuid4()), "PERSIST", self.NOW_VALID)

        from kiosk.domain.models.value_objects import CouponId
        saved = coupon_repo.find_by_id(CouponId.from_str(dto.coupon_id))
        assert saved.usage_count == 1
