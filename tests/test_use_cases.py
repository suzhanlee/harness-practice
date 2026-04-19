import pytest
from decimal import Decimal

from kiosk.application.use_cases.get_menu import GetMenuUseCase
from kiosk.application.use_cases.place_order import PlaceOrderUseCase, OrderItemRequest
from kiosk.application.use_cases.process_payment import ProcessPaymentUseCase
from kiosk.application.use_cases.cart_use_cases import SetStockUseCase, AddToCartUseCase
from kiosk.domain.models.payment import PaymentStatus
from kiosk.domain.services.inventory_domain_service import InventoryDomainService
from kiosk.infrastructure.repositories.in_memory_menu_item_repository import InMemoryMenuItemRepository


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
