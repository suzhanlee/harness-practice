import pytest
from decimal import Decimal

from kiosk.application.use_cases.get_menu import GetMenuUseCase
from kiosk.application.use_cases.place_order import PlaceOrderUseCase, OrderItemRequest
from kiosk.application.use_cases.process_payment import ProcessPaymentUseCase
from kiosk.domain.models.payment import PaymentStatus


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
