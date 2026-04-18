import pytest
from decimal import Decimal

from kiosk.domain.models.user import User
from kiosk.domain.models.order import Order, OrderItem, OrderStatus
from kiosk.domain.models.value_objects import MenuItemId, Money, UserId
from kiosk.infrastructure.repositories.in_memory_user_repository import InMemoryUserRepository
from kiosk.infrastructure.repositories.in_memory_order_repository import InMemoryOrderRepository
from kiosk.application.use_cases.user_use_cases import CreateUserUseCase, AuthenticateUserUseCase
from kiosk.application.use_cases.order_history_use_cases import GetOrderHistoryUseCase, GetOrderDetailUseCase


class TestUserOrderIntegration:
    @pytest.fixture
    def repos(self):
        return {
            'user_repo': InMemoryUserRepository(),
            'order_repo': InMemoryOrderRepository(),
        }

    @pytest.fixture
    def use_cases(self, repos):
        return {
            'create_user': CreateUserUseCase(repos['user_repo']),
            'authenticate_user': AuthenticateUserUseCase(repos['user_repo']),
            'get_order_history': GetOrderHistoryUseCase(repos['order_repo']),
            'get_order_detail': GetOrderDetailUseCase(repos['order_repo']),
        }

    def test_create_user_and_authenticate(self, use_cases):
        create_user = use_cases['create_user']
        authenticate_user = use_cases['authenticate_user']

        # 사용자 생성
        user_dto = create_user.execute("user@example.com", "Test User")
        assert user_dto.email == "user@example.com"
        assert user_dto.name == "Test User"

        # 사용자 인증
        auth_user = authenticate_user.execute("user@example.com")
        assert auth_user is not None
        assert auth_user.user_id == user_dto.user_id

    def test_user_can_place_order(self, repos, use_cases):
        create_user = use_cases['create_user']
        user_repo = repos['user_repo']
        order_repo = repos['order_repo']

        # 사용자 생성
        user_dto = create_user.execute("user@example.com", "Test User")
        user_id = UserId.from_str(user_dto.user_id)

        # 주문 생성 및 사용자와 연결
        order = Order.create()
        order.user_id = user_id
        item = OrderItem(
            menu_item_id=MenuItemId.generate(),
            name="버거",
            unit_price=Money(Decimal("5000")),
            quantity=1
        )
        order.add_item(item)
        order.confirm()
        order.mark_paid()
        order_repo.save(order)

        # 사용자의 주문내역 조회
        get_order_history = use_cases['get_order_history']
        history = get_order_history.execute(user_dto.user_id)

        assert len(history) == 1
        assert history[0].order_id == str(order.id.value)
        assert history[0].status == "결제완료"

    def test_order_detail_shows_history(self, repos, use_cases):
        user_repo = repos['user_repo']
        order_repo = repos['order_repo']
        get_order_detail = use_cases['get_order_detail']

        # 주문 생성
        order = Order.create()
        item = OrderItem(
            menu_item_id=MenuItemId.generate(),
            name="음료",
            unit_price=Money(Decimal("2000")),
            quantity=2
        )
        order.add_item(item)
        order.confirm()
        order.mark_paid()
        order_repo.save(order)

        # 주문 상세 조회
        detail = get_order_detail.execute(str(order.id.value))

        assert detail.order_id == str(order.id.value)
        assert detail.status == "결제완료"
        assert detail.item_count == 2
        assert len(detail.history) >= 3  # 생성, 확인, 결제

    def test_multiple_orders_tracked_per_user(self, repos, use_cases):
        create_user = use_cases['create_user']
        user_repo = repos['user_repo']
        order_repo = repos['order_repo']
        get_order_history = use_cases['get_order_history']

        # 사용자 생성
        user_dto = create_user.execute("user@example.com", "Test User")
        user_id = UserId.from_str(user_dto.user_id)

        # 첫 번째 주문
        order1 = Order.create()
        order1.user_id = user_id
        order1.add_item(OrderItem(MenuItemId.generate(), "버거", Money(Decimal("5000")), 1))
        order1.confirm()
        order1.mark_paid()
        order_repo.save(order1)

        # 두 번째 주문
        order2 = Order.create()
        order2.user_id = user_id
        order2.add_item(OrderItem(MenuItemId.generate(), "음료", Money(Decimal("2000")), 2))
        order2.confirm()
        order2.mark_paid()
        order_repo.save(order2)

        # 주문내역 조회
        history = get_order_history.execute(user_dto.user_id)

        assert len(history) == 2
        assert history[0].total_amount == "5000"
        assert history[1].total_amount == "4000"
