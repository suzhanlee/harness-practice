import pytest
from decimal import Decimal

from kiosk.application.admin.manage_menu import AddMenuItemUseCase
from kiosk.application.admin.mark_menu_unavailable import MarkMenuUnavailableUseCase
from kiosk.domain.models.order import Order, OrderItem, OrderStatus
from kiosk.domain.models.value_objects import MenuItemId, Money
from kiosk.infrastructure.repositories.in_memory_menu_item_repository import InMemoryMenuItemRepository
from kiosk.infrastructure.repositories.in_memory_order_repository import InMemoryOrderRepository


@pytest.fixture
def menu_repo():
    return InMemoryMenuItemRepository()


@pytest.fixture
def order_repo():
    return InMemoryOrderRepository()


@pytest.fixture
def added_item(menu_repo):
    return AddMenuItemUseCase(menu_repo).execute("버거", Decimal("5000"), "버거")


class TestMarkMenuUnavailableUseCase:
    def test_mark_unavailable(self, menu_repo, order_repo, added_item):
        use_case = MarkMenuUnavailableUseCase(menu_repo, order_repo)
        dto = use_case.execute(added_item.id)
        assert dto.available is False
        assert dto.affected_orders == 0

    def test_mark_unavailable_persisted(self, menu_repo, order_repo, added_item):
        use_case = MarkMenuUnavailableUseCase(menu_repo, order_repo)
        use_case.execute(added_item.id)
        from kiosk.domain.models.value_objects import MenuItemId
        item = menu_repo.find_by_id(MenuItemId.from_str(added_item.id))
        assert item.available is False

    def test_mark_unavailable_updates_pending_orders(self, menu_repo, order_repo, added_item):
        mid = MenuItemId.from_str(added_item.id)
        order = Order.create()
        order.add_item(OrderItem(menu_item_id=mid, name="버거", unit_price=Money(Decimal("5000")), quantity=1))
        order_repo.save(order)

        use_case = MarkMenuUnavailableUseCase(menu_repo, order_repo)
        dto = use_case.execute(added_item.id)
        assert dto.affected_orders == 1

        saved_order = order_repo.find_by_id(order.id)
        assert saved_order.items[0].is_available is False

    def test_mark_unavailable_not_found_raises(self, menu_repo, order_repo):
        import uuid
        use_case = MarkMenuUnavailableUseCase(menu_repo, order_repo)
        with pytest.raises(ValueError, match="찾을 수 없습니다"):
            use_case.execute(str(uuid.uuid4()))
