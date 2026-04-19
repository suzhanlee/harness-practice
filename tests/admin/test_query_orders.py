import pytest
from decimal import Decimal

from kiosk.application.admin.query_orders import QueryOrdersUseCase
from kiosk.domain.models.order import Order, OrderItem
from kiosk.domain.models.value_objects import MenuItemId, Money
from kiosk.infrastructure.repositories.in_memory_order_repository import InMemoryOrderRepository


@pytest.fixture
def order_repo():
    return InMemoryOrderRepository()


def make_pending_order(order_repo: InMemoryOrderRepository) -> Order:
    order = Order.create()
    order.add_item(OrderItem(
        menu_item_id=MenuItemId.generate(),
        name="버거",
        unit_price=Money(Decimal("5000")),
        quantity=2,
    ))
    order_repo.save(order)
    return order


class TestQueryOrdersUseCase:
    def test_query_all_orders(self, order_repo):
        make_pending_order(order_repo)
        make_pending_order(order_repo)
        use_case = QueryOrdersUseCase(order_repo)
        result = use_case.execute()
        assert len(result) == 2

    def test_query_orders_empty(self, order_repo):
        use_case = QueryOrdersUseCase(order_repo)
        result = use_case.execute()
        assert result == []

    def test_query_orders_with_status_filter(self, order_repo):
        order = make_pending_order(order_repo)
        order.confirm()
        order_repo.save(order)
        make_pending_order(order_repo)

        use_case = QueryOrdersUseCase(order_repo)
        confirmed = use_case.execute(status_filter="확인됨")
        assert len(confirmed) == 1
        assert confirmed[0].status == "확인됨"

    def test_query_orders_dto_fields(self, order_repo):
        make_pending_order(order_repo)
        use_case = QueryOrdersUseCase(order_repo)
        result = use_case.execute()
        dto = result[0]
        assert dto.total_amount == Decimal("10000")
        assert dto.item_count == 2
        assert dto.status == "대기중"
