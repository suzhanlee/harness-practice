"""
tests/test_process_payment.py

태스크 9: ProcessPaymentUseCase 멤버십 오케스트레이션 확장 및 Receipt discount_breakdown 테스트.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from kiosk.application.events.dispatcher import EventDispatcher
from kiosk.application.use_cases.process_payment import ProcessPaymentUseCase
from kiosk.application.use_cases.place_order import PlaceOrderUseCase, OrderItemRequest
from kiosk.domain.events.member_events import PointsEarned
from kiosk.domain.models.member import Member, PointAccount
from kiosk.domain.models.value_objects import (
    MemberGrade,
    MemberId,
    Money,
    PointAccountId,
    UserId,
)
from kiosk.infrastructure.repositories.in_memory_member_repository import InMemoryMemberRepository


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _place_order(seeded_menu_repo, order_repo, domain_service):
    menu_items = seeded_menu_repo.find_available()
    place = PlaceOrderUseCase(seeded_menu_repo, order_repo, domain_service)
    return place.execute([OrderItemRequest(menu_item_id=str(menu_items[0].id.value), quantity=1)])


def _make_member(user_id_str: str) -> tuple[Member, UserId]:
    user_id = UserId.from_str(user_id_str)
    member_id = MemberId.generate()
    point_account = PointAccount(
        account_id=PointAccountId.generate(),
        balance=Money(Decimal("0")),
        grade=MemberGrade.NORMAL,
        total_paid=Money(Decimal("0")),
    )
    member = Member.register(
        member_id=member_id,
        user_id=user_id,
        name="테스터",
        email="tester@example.com",
        point_account=point_account,
    )
    return member, user_id


# ---------------------------------------------------------------------------
# 기존 테스트 호환성 — member_id=None (기본값) 동작 확인
# ---------------------------------------------------------------------------

class TestProcessPaymentBackwardCompat:
    """기존 서명(order_id, method)으로 호출해도 정상 동작해야 한다."""

    def test_execute_without_member_id_succeeds(
        self, seeded_menu_repo, order_repo, payment_repo, domain_service
    ):
        order_result = _place_order(seeded_menu_repo, order_repo, domain_service)
        use_case = ProcessPaymentUseCase(order_repo, payment_repo, domain_service)

        result = use_case.execute(order_result.order_id, "카드")

        assert result.success is True
        assert result.method == "카드"
        assert result.payment_id is not None

    def test_discount_breakdown_empty_when_no_discounts(
        self, seeded_menu_repo, order_repo, payment_repo, domain_service
    ):
        order_result = _place_order(seeded_menu_repo, order_repo, domain_service)
        use_case = ProcessPaymentUseCase(order_repo, payment_repo, domain_service)

        result = use_case.execute(order_result.order_id, "카드")

        assert isinstance(result.discount_breakdown, list)
        assert result.discount_breakdown == []


# ---------------------------------------------------------------------------
# 멤버십 오케스트레이션
# ---------------------------------------------------------------------------

class TestProcessPaymentMemberOrchestration:

    def test_member_points_earned_after_payment(
        self, seeded_menu_repo, order_repo, payment_repo, domain_service
    ):
        """결제 완료 후 회원 포인트가 적립되어야 한다."""
        member_repo = InMemoryMemberRepository()
        dispatcher = EventDispatcher()
        dispatched_events = []
        dispatcher.register(PointsEarned, lambda e: dispatched_events.append(e))

        import uuid
        user_id_str = str(uuid.uuid4())
        member, _ = _make_member(user_id_str)
        member_repo.save(member)

        order_result = _place_order(seeded_menu_repo, order_repo, domain_service)
        use_case = ProcessPaymentUseCase(
            order_repo,
            payment_repo,
            domain_service,
            member_repo=member_repo,
            dispatcher=dispatcher,
        )
        now = datetime(2026, 6, 1, 12, 0, 0)
        result = use_case.execute(order_result.order_id, "카드", member_id=user_id_str, now=now)

        assert result.success is True

        # 포인트 적립 이벤트가 dispatch됐는지 확인
        assert len(dispatched_events) == 1
        event = dispatched_events[0]
        assert isinstance(event, PointsEarned)
        assert event.member_id == member.member_id

        # 회원 포인트 잔액이 증가했는지 확인 (NORMAL 등급 1% 적립)
        saved_member = member_repo.find_by_user_id(member.user_id)
        assert saved_member.point_balance.amount > Decimal("0")

    def test_member_not_found_by_user_id_no_error(
        self, seeded_menu_repo, order_repo, payment_repo, domain_service
    ):
        """member_id를 전달했지만 find_by_user_id가 None을 반환하면 에러 없이 완료한다."""
        member_repo = InMemoryMemberRepository()
        dispatcher = EventDispatcher()

        import uuid
        unknown_user_id = str(uuid.uuid4())

        order_result = _place_order(seeded_menu_repo, order_repo, domain_service)
        use_case = ProcessPaymentUseCase(
            order_repo,
            payment_repo,
            domain_service,
            member_repo=member_repo,
            dispatcher=dispatcher,
        )
        result = use_case.execute(order_result.order_id, "카드", member_id=unknown_user_id)

        assert result.success is True

    def test_member_id_none_no_membership_processing(
        self, seeded_menu_repo, order_repo, payment_repo, domain_service
    ):
        """member_id=None이면 멤버십 처리 없이 성공해야 한다."""
        member_repo = InMemoryMemberRepository()
        dispatcher = EventDispatcher()
        dispatched_events = []
        dispatcher.register(PointsEarned, lambda e: dispatched_events.append(e))

        order_result = _place_order(seeded_menu_repo, order_repo, domain_service)
        use_case = ProcessPaymentUseCase(
            order_repo,
            payment_repo,
            domain_service,
            member_repo=member_repo,
            dispatcher=dispatcher,
        )
        result = use_case.execute(order_result.order_id, "카드", member_id=None)

        assert result.success is True
        assert dispatched_events == []


# ---------------------------------------------------------------------------
# discount_breakdown 필드 검증
# ---------------------------------------------------------------------------

class TestProcessPaymentDiscountBreakdown:

    def _make_confirmed_order_with_discount(self, seeded_menu_repo, order_repo, domain_service, discount_rule):
        """PENDING 상태에서 할인 적용 후 confirm하여 저장된 주문을 반환."""
        from kiosk.domain.models.order import Order, OrderItem
        from kiosk.domain.models.value_objects import MenuItemId

        menu_items = seeded_menu_repo.find_available()
        menu_item = menu_items[0]

        order = Order.create()
        order_item = domain_service.create_order_item_from_menu(menu_item, 1)
        order.add_item(order_item)

        # PENDING 상태에서 할인 적용
        order.apply_discount(discount_rule)

        order.confirm()
        order_repo.save(order)
        return order

    def test_discount_breakdown_contains_rule_info(
        self, seeded_menu_repo, order_repo, payment_repo, domain_service
    ):
        """할인 규칙이 적용된 주문의 경우 discount_breakdown에 규칙 정보가 담겨야 한다."""
        from kiosk.domain.models.value_objects import FixedDiscountRule

        discount_rule = FixedDiscountRule(amount=Money(Decimal("500")))
        order = self._make_confirmed_order_with_discount(
            seeded_menu_repo, order_repo, domain_service, discount_rule
        )

        use_case = ProcessPaymentUseCase(order_repo, payment_repo, domain_service)
        result = use_case.execute(str(order.id.value), "카드")

        assert len(result.discount_breakdown) == 1
        entry = result.discount_breakdown[0]
        assert "rule_name" in entry
        assert "discount_amount" in entry
        assert entry["rule_name"] == "FixedDiscountRule"
        assert entry["discount_amount"] == "500"

    def test_amount_paid_reflects_discount(
        self, seeded_menu_repo, order_repo, payment_repo, domain_service
    ):
        """amount_paid는 할인 후 최종 금액이어야 한다."""
        from kiosk.domain.models.value_objects import FixedDiscountRule

        discount_amount = Decimal("500")
        discount_rule = FixedDiscountRule(amount=Money(discount_amount))
        order = self._make_confirmed_order_with_discount(
            seeded_menu_repo, order_repo, domain_service, discount_rule
        )
        original_total = order.total_amount.amount

        use_case = ProcessPaymentUseCase(order_repo, payment_repo, domain_service)
        result = use_case.execute(str(order.id.value), "카드")

        expected_paid = original_total - discount_amount
        assert Decimal(result.amount_paid) == expected_paid
