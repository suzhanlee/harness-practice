"""PointAccount 단위 테스트.

earn() 후 balance 증가 확인, redeem() 잔액 부족 에러 메시지 고정 확인,
promote_if_eligible() 등급 변경 조건 테스트를 담는다.
"""
from datetime import datetime
from decimal import Decimal

import pytest

from kiosk.domain.events.member_events import GradeUpgraded, PointsEarned
from kiosk.domain.models.member import PointAccount
from kiosk.domain.models.value_objects import (
    InsufficientPointBalanceError,
    MemberGrade,
    MemberId,
    Money,
    OrderId,
    PointAccountId,
)

_NOW = datetime(2026, 6, 1, 12, 0, 0)


def _make_account(
    grade: MemberGrade = MemberGrade.NORMAL,
    balance: Decimal = Decimal("0"),
    total_paid: Decimal = Decimal("0"),
) -> PointAccount:
    return PointAccount(
        account_id=PointAccountId.generate(),
        balance=Money(balance),
        grade=grade,
        total_paid=Money(total_paid),
    )


# ──────────────────────────────────────────────
# earn() 테스트
# ──────────────────────────────────────────────

class TestPointAccountEarn:
    def test_earn_increases_balance(self):
        """결제 후 balance가 적립률만큼 증가해야 한다 (NORMAL = 1%)."""
        account = _make_account(grade=MemberGrade.NORMAL, balance=Decimal("0"))
        member_id = MemberId.generate()
        order_id = OrderId.generate()

        account.earn(member_id, order_id, Money(Decimal("10000")), now=_NOW)

        # NORMAL 1% → 10000 * 1 / 100 = 100
        assert account.balance.amount == Decimal("100")

    def test_earn_accumulates_total_paid(self):
        """earn() 호출마다 total_paid가 누적돼야 한다."""
        account = _make_account()
        member_id = MemberId.generate()

        account.earn(member_id, OrderId.generate(), Money(Decimal("5000")), now=_NOW)
        account.earn(member_id, OrderId.generate(), Money(Decimal("3000")), now=_NOW)

        assert account.total_paid.amount == Decimal("8000")

    def test_earn_emits_points_earned_event(self):
        """earn() 호출 후 PointsEarned 이벤트가 pending에 쌓여야 한다."""
        account = _make_account()
        member_id = MemberId.generate()
        order_id = OrderId.generate()

        account.earn(member_id, order_id, Money(Decimal("10000")), now=_NOW)
        events = account.pull_pending_events()

        assert len(events) == 1
        assert isinstance(events[0], PointsEarned)
        assert events[0].member_id == member_id
        assert events[0].order_id == order_id

    def test_earn_vip_rate(self):
        """VIP 등급은 5% 적립률이 적용돼야 한다."""
        account = _make_account(grade=MemberGrade.VIP, balance=Decimal("0"))
        member_id = MemberId.generate()

        account.earn(member_id, OrderId.generate(), Money(Decimal("10000")), now=_NOW)

        # VIP 5% → 10000 * 5 / 100 = 500
        assert account.balance.amount == Decimal("500")

    def test_earn_increments_version(self):
        """earn() 호출 시 version이 증가해야 한다."""
        account = _make_account()
        initial_version = account.version

        account.earn(MemberId.generate(), OrderId.generate(), Money(Decimal("1000")), now=_NOW)

        assert account.version == initial_version + 1


# ──────────────────────────────────────────────
# redeem() 테스트
# ──────────────────────────────────────────────

class TestPointAccountRedeem:
    def test_redeem_decreases_balance(self):
        """redeem() 후 balance가 요청 금액만큼 차감돼야 한다."""
        account = _make_account(balance=Decimal("1000"))

        account.redeem(Money(Decimal("300")))

        assert account.balance.amount == Decimal("700")

    def test_redeem_exact_balance_succeeds(self):
        """잔액 전액을 redeem할 수 있어야 한다."""
        account = _make_account(balance=Decimal("500"))

        account.redeem(Money(Decimal("500")))

        assert account.balance.amount == Decimal("0")

    def test_redeem_insufficient_balance_raises(self):
        """잔액이 부족할 때 InsufficientPointBalanceError가 발생해야 한다."""
        account = _make_account(balance=Decimal("100"))

        with pytest.raises(InsufficientPointBalanceError):
            account.redeem(Money(Decimal("200")))

    def test_redeem_insufficient_balance_error_message(self):
        """에러 메시지에 현재 잔액과 요청 금액이 포함돼야 한다."""
        account = _make_account(balance=Decimal("100"))

        with pytest.raises(InsufficientPointBalanceError) as exc_info:
            account.redeem(Money(Decimal("200")))

        msg = str(exc_info.value)
        assert "100" in msg, "에러 메시지에 현재 잔액(100)이 포함돼야 한다."
        assert "200" in msg, "에러 메시지에 요청 금액(200)이 포함돼야 한다."

    def test_redeem_increments_version(self):
        """redeem() 호출 시 version이 증가해야 한다."""
        account = _make_account(balance=Decimal("1000"))
        initial_version = account.version

        account.redeem(Money(Decimal("100")))

        assert account.version == initial_version + 1


# ──────────────────────────────────────────────
# promote_if_eligible() 테스트
# ──────────────────────────────────────────────

class TestPromoteIfEligible:
    def test_no_promotion_below_threshold(self):
        """누적 결제액이 기준 미만이면 등급 변경 없음."""
        account = _make_account(grade=MemberGrade.NORMAL, total_paid=Decimal("50000"))
        member_id = MemberId.generate()

        account.promote_if_eligible(member_id, now=_NOW)

        assert account.grade == MemberGrade.NORMAL
        events = account.pull_pending_events()
        assert len(events) == 0

    def test_promote_normal_to_silver(self):
        """누적 결제액 10만원 이상이면 NORMAL → SILVER 승급."""
        account = _make_account(grade=MemberGrade.NORMAL, total_paid=Decimal("100000"))
        member_id = MemberId.generate()

        account.promote_if_eligible(member_id, now=_NOW)

        assert account.grade == MemberGrade.SILVER

    def test_promote_emits_grade_upgraded_event(self):
        """등급 승급 시 GradeUpgraded 이벤트가 발행돼야 한다."""
        account = _make_account(grade=MemberGrade.NORMAL, total_paid=Decimal("100000"))
        member_id = MemberId.generate()

        account.promote_if_eligible(member_id, now=_NOW)
        events = account.pull_pending_events()

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, GradeUpgraded)
        assert event.old_grade == MemberGrade.NORMAL
        assert event.new_grade == MemberGrade.SILVER
        assert event.member_id == member_id

    def test_promote_normal_to_gold(self):
        """누적 결제액 30만원 이상이면 GOLD 승급."""
        account = _make_account(grade=MemberGrade.NORMAL, total_paid=Decimal("300000"))
        member_id = MemberId.generate()

        account.promote_if_eligible(member_id, now=_NOW)

        assert account.grade == MemberGrade.GOLD

    def test_promote_normal_to_vip(self):
        """누적 결제액 100만원 이상이면 VIP 승급."""
        account = _make_account(grade=MemberGrade.NORMAL, total_paid=Decimal("1000000"))
        member_id = MemberId.generate()

        account.promote_if_eligible(member_id, now=_NOW)

        assert account.grade == MemberGrade.VIP

    def test_no_event_when_already_highest_grade(self):
        """이미 VIP 등급이면 승급 이벤트 없음."""
        account = _make_account(grade=MemberGrade.VIP, total_paid=Decimal("5000000"))
        member_id = MemberId.generate()

        account.promote_if_eligible(member_id, now=_NOW)

        events = account.pull_pending_events()
        assert len(events) == 0

    def test_no_promotion_if_already_at_correct_grade(self):
        """이미 적합한 등급에 있으면 이벤트 미발행."""
        account = _make_account(grade=MemberGrade.SILVER, total_paid=Decimal("150000"))
        member_id = MemberId.generate()

        account.promote_if_eligible(member_id, now=_NOW)

        assert account.grade == MemberGrade.SILVER
        events = account.pull_pending_events()
        assert len(events) == 0

    def test_pull_pending_events_clears_list(self):
        """pull_pending_events() 호출 후 내부 목록이 비워져야 한다."""
        account = _make_account(grade=MemberGrade.NORMAL, total_paid=Decimal("100000"))
        member_id = MemberId.generate()

        account.promote_if_eligible(member_id, now=_NOW)
        account.pull_pending_events()  # 첫 번째 호출로 비움
        events_second = account.pull_pending_events()

        assert events_second == []
