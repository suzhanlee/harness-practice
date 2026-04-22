"""E2E 멤버십 플로우 통합 테스트.

'회원가입 → 주문 → VIP 할인+쿠폰+포인트 적용 → 결제 → 포인트 적립 → 등급 업그레이드'
전체 흐름과 비회원 결제, 포인트 이중 사용 시나리오를 검증한다.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List

import pytest

from kiosk.application.events.dispatcher import EventDispatcher
from kiosk.application.use_cases.place_order import OrderItemRequest, PlaceOrderUseCase
from kiosk.application.use_cases.process_payment import ProcessPaymentUseCase
from kiosk.application.use_cases.register_member import RegisterMemberUseCase
from kiosk.domain.events.member_events import GradeUpgraded, PointsEarned
from kiosk.domain.models.member import Member, PointAccount
from kiosk.domain.models.value_objects import (
    InsufficientPointBalanceError,
    MemberGrade,
    MemberId,
    Money,
    PointAccountId,
    UserId,
)
from kiosk.infrastructure.repositories.in_memory_member_repository import (
    InMemoryMemberRepository,
)
from kiosk.infrastructure.repositories.in_memory_menu_item_repository import (
    InMemoryMenuItemRepository,
)
from kiosk.infrastructure.repositories.in_memory_order_repository import (
    InMemoryOrderRepository,
)
from kiosk.infrastructure.repositories.in_memory_payment_repository import (
    InMemoryPaymentRepository,
)
from kiosk.infrastructure.seed_data import seed_menu


# ---------------------------------------------------------------------------
# 공통 헬퍼
# ---------------------------------------------------------------------------

def _build_deps():
    """테스트용 의존성 컨테이너를 구성해 반환한다."""
    menu_repo = InMemoryMenuItemRepository()
    seed_menu(menu_repo)
    order_repo = InMemoryOrderRepository()
    payment_repo = InMemoryPaymentRepository()
    member_repo = InMemoryMemberRepository()

    from kiosk.domain.services.order_domain_service import OrderDomainService
    domain_service = OrderDomainService()

    dispatcher = EventDispatcher()

    return {
        "menu_repo": menu_repo,
        "order_repo": order_repo,
        "payment_repo": payment_repo,
        "member_repo": member_repo,
        "domain_service": domain_service,
        "dispatcher": dispatcher,
    }


def _place_confirmed_order(deps, quantity: int = 1) -> str:
    """메뉴에서 첫 번째 아이템을 주문하고 주문 ID를 반환한다."""
    menu_items = deps["menu_repo"].find_available()
    use_case = PlaceOrderUseCase(
        deps["menu_repo"], deps["order_repo"], deps["domain_service"]
    )
    result = use_case.execute(
        [OrderItemRequest(menu_item_id=str(menu_items[0].id.value), quantity=quantity)]
    )
    return result.order_id


def _register_member(deps, grade: MemberGrade = MemberGrade.NORMAL, balance: Decimal = Decimal("0")) -> tuple[str, str]:
    """회원을 등록하고 (user_id_str, member_id_str) 튜플을 반환한다."""
    user_id_str = str(uuid.uuid4())
    register_uc = RegisterMemberUseCase(deps["member_repo"])
    dto = register_uc.execute(user_id_str, "테스터", "tester@example.com")

    # 특정 등급/잔액이 필요한 경우 직접 세팅
    if grade != MemberGrade.NORMAL or balance > Decimal("0"):
        uid = UserId.from_str(user_id_str)
        member = deps["member_repo"].find_by_user_id(uid)
        # 등급과 잔액 재설정 (테스트 픽스처 전용)
        new_account = PointAccount(
            account_id=member.point_account.account_id,
            balance=Money(balance),
            grade=grade,
            total_paid=member.point_account.total_paid,
        )
        from kiosk.domain.models.member import Member as MemberCls
        updated = MemberCls.register(
            member_id=member.member_id,
            user_id=member.user_id,
            name=member.name,
            email=member.email,
            point_account=new_account,
        )
        deps["member_repo"].save(updated)

    return user_id_str, dto.member_id


# ---------------------------------------------------------------------------
# 1. E2E: 회원가입 → 주문 → 복합 할인 → 결제 → 포인트 적립 → 등급 업그레이드
# ---------------------------------------------------------------------------

class TestMembershipFlowE2E:
    """전체 멤버십 플로우 E2E 테스트."""

    def test_full_membership_flow_vip_coupon_point(self):
        """VIP 할인 + 쿠폰 + 포인트 적용 후 결제하면 포인트가 적립된다."""
        deps = _build_deps()

        # 1) 회원 가입 (VIP 등급, 포인트 잔액 2000)
        user_id_str, _ = _register_member(deps, grade=MemberGrade.VIP, balance=Decimal("2000"))

        # 2) 주문 생성 (메뉴 첫 번째 아이템)
        order_id = _place_confirmed_order(deps)

        # 3) 결제 전 Order에서 할인 적용 불가 (CONFIRMED 상태) — ProcessPaymentUseCase가 담당
        #    할인은 PENDING 상태에서만 가능하므로 Order를 꺼내 할인 적용 후 재저장
        from kiosk.domain.models.discount_rules import (
            CouponDiscountRule,
            PointRedemptionRule,
            VipGradeDiscountRule,
        )
        from kiosk.domain.models.value_objects import OrderId

        order_repo = deps["order_repo"]
        oid = OrderId.from_str(order_id)
        # PlaceOrderUseCase가 이미 confirm()했으므로 직접 PENDING Order로 재구성
        # 테스트용으로 별도 PENDING order 생성 후 할인 적용
        from kiosk.domain.models.order import Order, OrderItem
        from kiosk.domain.models.value_objects import MenuItemId

        menu_items = deps["menu_repo"].find_available()
        new_order = Order.create()
        order_item = deps["domain_service"].create_order_item_from_menu(menu_items[0], 1)
        new_order.add_item(order_item)

        vip_rule = VipGradeDiscountRule(grade=MemberGrade.VIP)
        coupon_rule = CouponDiscountRule(coupon_discount_amount=Money(Decimal("500")))
        point_rule = PointRedemptionRule(points_to_redeem=Money(Decimal("1000")))

        new_order.apply_discount(vip_rule)
        new_order.apply_discount(coupon_rule)
        new_order.apply_discount(point_rule)
        new_order.confirm()
        order_repo.save(new_order)
        new_order_id = str(new_order.id.value)

        # 4) 이벤트 수집
        dispatched: List = []
        deps["dispatcher"].register(PointsEarned, lambda e: dispatched.append(e))
        deps["dispatcher"].register(GradeUpgraded, lambda e: dispatched.append(e))

        # 5) 결제 실행
        now = datetime(2026, 6, 1, 12, 0, 0)
        use_case = ProcessPaymentUseCase(
            deps["order_repo"],
            deps["payment_repo"],
            deps["domain_service"],
            member_repo=deps["member_repo"],
            dispatcher=deps["dispatcher"],
        )
        result = use_case.execute(new_order_id, "카드", member_id=user_id_str, now=now)

        assert result.success is True

        # 6) 포인트 적립 이벤트 발행 확인
        points_earned_events = [e for e in dispatched if isinstance(e, PointsEarned)]
        assert len(points_earned_events) == 1
        event = points_earned_events[0]
        assert event.points_earned.amount > Decimal("0")

        # 7) 회원 포인트 잔액 증가 확인
        uid = UserId.from_str(user_id_str)
        saved_member = deps["member_repo"].find_by_user_id(uid)
        assert saved_member.point_balance.amount > Decimal("0")

        # 8) discount_breakdown 필드 확인
        assert len(result.discount_breakdown) == 3

    def test_grade_upgrade_event_dispatched_after_payment(self):
        """결제 누적액이 등급 승급 기준을 초과하면 GradeUpgraded 이벤트가 발행된다."""
        deps = _build_deps()

        # NORMAL 등급 회원, 누적 결제액 99,000원 (SILVER 기준 100,000원 미만)
        user_id_str, _ = _register_member(deps, grade=MemberGrade.NORMAL, balance=Decimal("0"))
        uid = UserId.from_str(user_id_str)

        # total_paid를 99,000으로 설정
        member = deps["member_repo"].find_by_user_id(uid)
        new_account = PointAccount(
            account_id=member.point_account.account_id,
            balance=Money(Decimal("0")),
            grade=MemberGrade.NORMAL,
            total_paid=Money(Decimal("99000")),
        )
        from kiosk.domain.models.member import Member as MemberCls
        updated = MemberCls.register(
            member_id=member.member_id,
            user_id=member.user_id,
            name=member.name,
            email=member.email,
            point_account=new_account,
        )
        deps["member_repo"].save(updated)

        # 주문 생성 (5500원 이상 → 누적 100,000원 초과 → SILVER 승급)
        order_id = _place_confirmed_order(deps)

        dispatched: List = []
        deps["dispatcher"].register(GradeUpgraded, lambda e: dispatched.append(e))

        now = datetime(2026, 6, 1, 12, 0, 0)
        use_case = ProcessPaymentUseCase(
            deps["order_repo"],
            deps["payment_repo"],
            deps["domain_service"],
            member_repo=deps["member_repo"],
            dispatcher=deps["dispatcher"],
        )
        use_case.execute(order_id, "카드", member_id=user_id_str, now=now)

        grade_upgraded_events = [e for e in dispatched if isinstance(e, GradeUpgraded)]
        assert len(grade_upgraded_events) == 1
        event = grade_upgraded_events[0]
        assert event.old_grade == MemberGrade.NORMAL
        assert event.new_grade == MemberGrade.SILVER


# ---------------------------------------------------------------------------
# 2. PointsEarned 이벤트 디스패처 전달 확인
# ---------------------------------------------------------------------------

class TestPointsEarnedEventDispatched:
    """PointsEarned 이벤트가 EventDispatcher를 통해 핸들러에 전달되는지 확인한다."""

    def test_points_earned_event_reaches_handler(self):
        """결제 후 PointsEarned 이벤트가 등록된 핸들러에 전달된다."""
        deps = _build_deps()
        user_id_str, _ = _register_member(deps)

        order_id = _place_confirmed_order(deps)

        received_events: List[PointsEarned] = []
        deps["dispatcher"].register(PointsEarned, lambda e: received_events.append(e))

        now = datetime(2026, 6, 1, 12, 0, 0)
        use_case = ProcessPaymentUseCase(
            deps["order_repo"],
            deps["payment_repo"],
            deps["domain_service"],
            member_repo=deps["member_repo"],
            dispatcher=deps["dispatcher"],
        )
        use_case.execute(order_id, "카드", member_id=user_id_str, now=now)

        assert len(received_events) == 1
        event = received_events[0]
        assert isinstance(event, PointsEarned)
        assert event.points_earned.amount > Decimal("0")
        assert event.new_balance.amount > Decimal("0")

    def test_points_earned_event_contains_correct_member_id(self):
        """PointsEarned 이벤트의 member_id가 실제 회원의 member_id와 일치한다."""
        deps = _build_deps()
        user_id_str, member_id_str = _register_member(deps)

        uid = UserId.from_str(user_id_str)
        member = deps["member_repo"].find_by_user_id(uid)

        order_id = _place_confirmed_order(deps)

        received_events: List[PointsEarned] = []
        deps["dispatcher"].register(PointsEarned, lambda e: received_events.append(e))

        use_case = ProcessPaymentUseCase(
            deps["order_repo"],
            deps["payment_repo"],
            deps["domain_service"],
            member_repo=deps["member_repo"],
            dispatcher=deps["dispatcher"],
        )
        use_case.execute(order_id, "카드", member_id=user_id_str)

        assert received_events[0].member_id == member.member_id


# ---------------------------------------------------------------------------
# 3. 포인트 이중 사용 시나리오 — InsufficientPointBalanceError
# ---------------------------------------------------------------------------

class TestInsufficientPointBalance:
    """잔액보다 많은 포인트 차감 시 InsufficientPointBalanceError가 발생한다."""

    def test_spend_more_points_than_balance_raises_error(self):
        """잔액이 1000원인데 2000원을 차감하려 하면 InsufficientPointBalanceError가 발생한다."""
        deps = _build_deps()
        user_id_str, _ = _register_member(deps, balance=Decimal("1000"))

        uid = UserId.from_str(user_id_str)
        member = deps["member_repo"].find_by_user_id(uid)

        with pytest.raises(InsufficientPointBalanceError):
            member.spend_points(Money(Decimal("2000")))

    def test_spend_exact_balance_succeeds(self):
        """잔액과 동일한 금액을 차감하면 성공하고 잔액이 0이 된다."""
        deps = _build_deps()
        user_id_str, _ = _register_member(deps, balance=Decimal("1000"))

        uid = UserId.from_str(user_id_str)
        member = deps["member_repo"].find_by_user_id(uid)

        member.spend_points(Money(Decimal("1000")))
        assert member.point_balance.amount == Decimal("0")

    def test_spend_zero_when_balance_is_zero_raises_error(self):
        """잔액이 0인 상태에서 포인트를 차감하면 에러가 발생한다."""
        deps = _build_deps()
        user_id_str, _ = _register_member(deps, balance=Decimal("0"))

        uid = UserId.from_str(user_id_str)
        member = deps["member_repo"].find_by_user_id(uid)

        with pytest.raises(InsufficientPointBalanceError):
            member.spend_points(Money(Decimal("100")))

    def test_double_spend_scenario(self):
        """첫 번째 차감은 성공하지만 이미 잔액이 없어진 상태에서 재시도하면 에러가 발생한다."""
        deps = _build_deps()
        user_id_str, _ = _register_member(deps, balance=Decimal("500"))

        uid = UserId.from_str(user_id_str)
        member = deps["member_repo"].find_by_user_id(uid)

        # 첫 번째 차감 성공
        member.spend_points(Money(Decimal("500")))
        assert member.point_balance.amount == Decimal("0")

        # 두 번째 차감 실패
        with pytest.raises(InsufficientPointBalanceError):
            member.spend_points(Money(Decimal("500")))


# ---------------------------------------------------------------------------
# 4. 비회원 결제 — member_id=None 시 포인트 적립/VIP 할인 없이 정상 완료
# ---------------------------------------------------------------------------

class TestGuestPaymentFlow:
    """비회원(member_id=None) 결제 시나리오."""

    def test_guest_payment_succeeds_without_membership(self):
        """비회원 결제는 member_id 없이 성공해야 한다."""
        deps = _build_deps()
        order_id = _place_confirmed_order(deps)

        use_case = ProcessPaymentUseCase(
            deps["order_repo"],
            deps["payment_repo"],
            deps["domain_service"],
        )
        result = use_case.execute(order_id, "카드", member_id=None)

        assert result.success is True
        assert result.payment_id is not None

    def test_guest_payment_dispatches_no_points_earned_event(self):
        """비회원 결제 시 PointsEarned 이벤트가 발행되지 않는다."""
        deps = _build_deps()
        order_id = _place_confirmed_order(deps)

        dispatched: List = []
        deps["dispatcher"].register(PointsEarned, lambda e: dispatched.append(e))
        deps["dispatcher"].register(GradeUpgraded, lambda e: dispatched.append(e))

        use_case = ProcessPaymentUseCase(
            deps["order_repo"],
            deps["payment_repo"],
            deps["domain_service"],
            member_repo=deps["member_repo"],
            dispatcher=deps["dispatcher"],
        )
        use_case.execute(order_id, "카드", member_id=None)

        assert dispatched == []

    def test_guest_payment_no_vip_discount_by_default(self):
        """비회원 주문에는 VIP 할인이 적용되지 않으므로 원가로 결제된다."""
        deps = _build_deps()
        menu_items = deps["menu_repo"].find_available()
        first_item = menu_items[0]
        original_price = first_item.price.amount

        order_id = _place_confirmed_order(deps)

        use_case = ProcessPaymentUseCase(
            deps["order_repo"],
            deps["payment_repo"],
            deps["domain_service"],
        )
        result = use_case.execute(order_id, "현금", member_id=None)

        assert Decimal(result.amount_paid) == original_price
        assert result.discount_breakdown == []

    def test_guest_payment_coupon_discount_applied(self):
        """비회원이라도 쿠폰 할인은 적용 가능하다."""
        deps = _build_deps()
        from kiosk.domain.models.discount_rules import CouponDiscountRule
        from kiosk.domain.models.order import Order, OrderItem
        from kiosk.domain.models.value_objects import MenuItemId

        menu_items = deps["menu_repo"].find_available()
        order = Order.create()
        order_item = deps["domain_service"].create_order_item_from_menu(menu_items[0], 1)
        order.add_item(order_item)

        coupon_rule = CouponDiscountRule(coupon_discount_amount=Money(Decimal("500")))
        order.apply_discount(coupon_rule)
        order.confirm()
        deps["order_repo"].save(order)

        original_total = menu_items[0].price.amount

        use_case = ProcessPaymentUseCase(
            deps["order_repo"],
            deps["payment_repo"],
            deps["domain_service"],
        )
        result = use_case.execute(str(order.id.value), "카드", member_id=None)

        assert result.success is True
        expected = original_total - Decimal("500")
        assert Decimal(result.amount_paid) == expected
        assert len(result.discount_breakdown) == 1
        assert result.discount_breakdown[0]["rule_name"] == "CouponDiscountRule"

    def test_guest_payment_member_points_not_affected(self):
        """비회원 결제 시 기존 회원의 포인트 잔액에 영향을 주지 않는다."""
        deps = _build_deps()

        # 별도 회원 등록
        user_id_str, _ = _register_member(deps, balance=Decimal("1000"))

        # 비회원으로 별도 주문 결제
        order_id = _place_confirmed_order(deps)
        use_case = ProcessPaymentUseCase(
            deps["order_repo"],
            deps["payment_repo"],
            deps["domain_service"],
            member_repo=deps["member_repo"],
            dispatcher=deps["dispatcher"],
        )
        use_case.execute(order_id, "카드", member_id=None)

        # 기존 회원 잔액 변화 없음
        uid = UserId.from_str(user_id_str)
        member = deps["member_repo"].find_by_user_id(uid)
        assert member.point_balance.amount == Decimal("1000")
