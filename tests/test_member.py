"""Member 애그리거트 단위 테스트.

now 파라미터 주입으로 결정적 테스트,
GradeUpgraded 이벤트 순서(PointsEarned → GradeUpgraded) 확인.
"""
from datetime import datetime
from decimal import Decimal

import pytest

from kiosk.domain.events.member_events import GradeUpgraded, PointsEarned
from kiosk.domain.models.member import Member, PointAccount
from kiosk.domain.models.value_objects import (
    InsufficientPointBalanceError,
    MemberGrade,
    MemberId,
    Money,
    OrderId,
    PointAccountId,
    UserId,
)

_NOW = datetime(2026, 6, 1, 12, 0, 0)


def _make_member(
    grade: MemberGrade = MemberGrade.NORMAL,
    balance: Decimal = Decimal("0"),
    total_paid: Decimal = Decimal("0"),
    name: str = "홍길동",
    email: str = "hong@example.com",
) -> Member:
    member_id = MemberId.generate()
    user_id = UserId.generate()
    account = PointAccount(
        account_id=PointAccountId.generate(),
        balance=Money(balance),
        grade=grade,
        total_paid=Money(total_paid),
    )
    return Member.register(
        member_id=member_id,
        user_id=user_id,
        name=name,
        email=email,
        point_account=account,
    )


# ──────────────────────────────────────────────
# Member 생성 테스트
# ──────────────────────────────────────────────

class TestMemberCreation:
    def test_register_creates_member_with_correct_grade(self):
        """register()로 생성된 멤버의 grade가 PointAccount grade와 일치해야 한다."""
        member = _make_member(grade=MemberGrade.SILVER)

        assert member.grade == MemberGrade.SILVER

    def test_register_creates_member_with_correct_balance(self):
        """register()로 생성된 멤버의 point_balance가 설정값과 일치해야 한다."""
        member = _make_member(balance=Decimal("5000"))

        assert member.point_balance.amount == Decimal("5000")

    def test_point_account_accessible_via_property(self):
        """point_account 프로퍼티로 PointAccount에 접근할 수 있어야 한다."""
        member = _make_member()

        assert member.point_account is not None
        assert isinstance(member.point_account, PointAccount)


# ──────────────────────────────────────────────
# apply_payment() — 포인트 적립 + 등급 승급
# ──────────────────────────────────────────────

class TestApplyPayment:
    def test_apply_payment_increases_balance(self):
        """apply_payment() 후 포인트 잔액이 증가해야 한다."""
        member = _make_member(grade=MemberGrade.NORMAL, balance=Decimal("0"))
        order_id = OrderId.generate()

        member.apply_payment(order_id, Money(Decimal("10000")), now=_NOW)

        # NORMAL 1% → 100
        assert member.point_balance.amount == Decimal("100")

    def test_apply_payment_emits_points_earned_event(self):
        """apply_payment() 후 PointsEarned 이벤트가 발행돼야 한다."""
        member = _make_member()
        order_id = OrderId.generate()

        member.apply_payment(order_id, Money(Decimal("10000")), now=_NOW)
        events = member.pull_domain_events()

        assert any(isinstance(e, PointsEarned) for e in events)

    def test_apply_payment_without_grade_change_no_grade_event(self):
        """등급 변경이 없으면 GradeUpgraded 이벤트가 발행되지 않아야 한다."""
        member = _make_member(grade=MemberGrade.NORMAL, total_paid=Decimal("0"))
        order_id = OrderId.generate()

        # 50000원 결제 — 누적 5만원, 아직 SILVER(10만원) 미달
        member.apply_payment(order_id, Money(Decimal("50000")), now=_NOW)
        events = member.pull_domain_events()

        assert not any(isinstance(e, GradeUpgraded) for e in events)

    def test_apply_payment_with_grade_upgrade_emits_both_events(self):
        """등급 승급 시 PointsEarned → GradeUpgraded 순서로 이벤트가 발행돼야 한다."""
        # 누적 99000원에서 1000원을 더 결제해 100000원 달성 → SILVER 승급
        member = _make_member(grade=MemberGrade.NORMAL, total_paid=Decimal("99000"))
        order_id = OrderId.generate()

        member.apply_payment(order_id, Money(Decimal("1000")), now=_NOW)
        events = member.pull_domain_events()

        event_types = [type(e) for e in events]
        assert PointsEarned in event_types
        assert GradeUpgraded in event_types

        # 순서: PointsEarned가 GradeUpgraded보다 앞에 위치해야 한다
        points_idx = next(i for i, e in enumerate(events) if isinstance(e, PointsEarned))
        grade_idx = next(i for i, e in enumerate(events) if isinstance(e, GradeUpgraded))
        assert points_idx < grade_idx, "PointsEarned는 GradeUpgraded보다 먼저 발행돼야 한다."

    def test_apply_payment_grade_upgrade_to_silver(self):
        """누적 10만원 달성 시 NORMAL → SILVER로 승급돼야 한다."""
        member = _make_member(grade=MemberGrade.NORMAL, total_paid=Decimal("90000"))
        order_id = OrderId.generate()

        member.apply_payment(order_id, Money(Decimal("10000")), now=_NOW)

        assert member.grade == MemberGrade.SILVER

    def test_apply_payment_now_is_deterministic(self):
        """now 파라미터를 주입하면 이벤트의 occurred_at이 고정돼야 한다."""
        member = _make_member()
        order_id = OrderId.generate()
        fixed_time = datetime(2026, 1, 1, 0, 0, 0)

        member.apply_payment(order_id, Money(Decimal("5000")), now=fixed_time)
        events = member.pull_domain_events()

        points_event = next(e for e in events if isinstance(e, PointsEarned))
        assert points_event.occurred_at == fixed_time


# ──────────────────────────────────────────────
# spend_points() 테스트
# ──────────────────────────────────────────────

class TestSpendPoints:
    def test_spend_points_decreases_balance(self):
        """spend_points() 후 잔액이 감소해야 한다."""
        member = _make_member(balance=Decimal("2000"))

        member.spend_points(Money(Decimal("500")))

        assert member.point_balance.amount == Decimal("1500")

    def test_spend_points_raises_when_insufficient(self):
        """잔액보다 많은 포인트 사용 시 InsufficientPointBalanceError가 발생해야 한다."""
        member = _make_member(balance=Decimal("100"))

        with pytest.raises(InsufficientPointBalanceError):
            member.spend_points(Money(Decimal("500")))


# ──────────────────────────────────────────────
# pull_domain_events() — 이벤트 수집 및 초기화
# ──────────────────────────────────────────────

class TestPullDomainEvents:
    def test_pull_domain_events_clears_after_call(self):
        """pull_domain_events() 호출 후 두 번째 호출은 빈 목록을 반환해야 한다."""
        member = _make_member()
        member.apply_payment(OrderId.generate(), Money(Decimal("5000")), now=_NOW)

        member.pull_domain_events()  # 첫 번째 — 소비
        events_second = member.pull_domain_events()

        assert events_second == []

    def test_pull_domain_events_includes_account_events(self):
        """PointAccount의 pending 이벤트가 pull_domain_events()에 포함돼야 한다."""
        member = _make_member()
        order_id = OrderId.generate()

        member.apply_payment(order_id, Money(Decimal("10000")), now=_NOW)
        events = member.pull_domain_events()

        assert any(isinstance(e, PointsEarned) for e in events)
