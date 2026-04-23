from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List

from kiosk.domain.events.base import DomainEvent
from kiosk.domain.events.member_events import GradeUpgraded, PointsEarned
from kiosk.domain.models.value_objects import (
    InsufficientPointBalanceError,
    MemberGrade,
    MemberId,
    Money,
    OrderId,
    PointAccountId,
    UserId,
)

# 등급 승급 누적 결제액 기준 (KRW)
_GRADE_THRESHOLDS = {
    MemberGrade.SILVER: Decimal("100000"),   # 10만원
    MemberGrade.GOLD: Decimal("300000"),     # 30만원
    MemberGrade.VIP: Decimal("1000000"),     # 100만원
}

_GRADE_ORDER = [MemberGrade.NORMAL, MemberGrade.SILVER, MemberGrade.GOLD, MemberGrade.VIP]


@dataclass
class PointAccount:
    """포인트 계좌 엔티티 — Member 애그리거트 내부에만 존재하며 외부에서 직접 쓰기 불가."""

    account_id: PointAccountId
    balance: Money
    grade: MemberGrade
    total_paid: Money
    version: int = 0
    _pending_events: List[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def earn(self, member_id: MemberId, order_id: OrderId, paid_amount: Money, now: datetime = None) -> None:
        """결제 금액에 따라 포인트 적립 후 PointsEarned 이벤트 기록."""
        rate = MemberGrade.earn_rate(self.grade)
        earn_amount = Money(
            (paid_amount.amount * rate / Decimal("100")).quantize(Decimal("1")),
            paid_amount.currency,
        )
        self.balance = self.balance + earn_amount
        self.total_paid = self.total_paid + paid_amount
        self.version += 1

        event = PointsEarned.create(
            member_id=member_id,
            order_id=order_id,
            points_earned=earn_amount,
            new_balance=self.balance,
            occurred_at=now,
        )
        self._pending_events.append(event)

    def redeem(self, amount: Money) -> None:
        """포인트 차감. 잔액 부족 시 InsufficientPointBalanceError 발생."""
        if self.balance.amount < amount.amount:
            raise InsufficientPointBalanceError(
                f"포인트 잔액이 부족합니다. 현재 잔액: {self.balance.amount}, 요청: {amount.amount}"
            )
        self.balance = Money(self.balance.amount - amount.amount, self.balance.currency)
        self.version += 1

    def promote_if_eligible(self, member_id: MemberId, now: datetime = None) -> None:
        """누적 결제액 기준으로 등급 승급 여부 확인 후 GradeUpgraded 이벤트 기록."""
        new_grade = self.grade

        for grade in reversed(_GRADE_ORDER):
            threshold = _GRADE_THRESHOLDS.get(grade)
            if threshold is None:
                continue
            if self.total_paid.amount >= threshold:
                new_grade = grade
                break

        if new_grade != self.grade:
            old_grade = self.grade
            self.grade = new_grade
            event = GradeUpgraded.create(
                member_id=member_id,
                old_grade=old_grade,
                new_grade=new_grade,
                occurred_at=now,
            )
            self._pending_events.append(event)

    def pull_pending_events(self) -> List[DomainEvent]:
        """발행 대기 중인 이벤트를 반환하고 내부 목록을 비운다."""
        events = list(self._pending_events)
        self._pending_events.clear()
        return events


@dataclass
class Member:
    """Member 애그리거트 루트. PointAccount를 내부 엔티티로 캡슐화한다."""

    member_id: MemberId
    user_id: UserId
    name: str
    email: str
    _point_account: PointAccount = field(repr=False)
    _pending_events: List[DomainEvent] = field(default_factory=list, init=False, repr=False)

    # ------------------------------------------------------------------
    # 팩토리
    # ------------------------------------------------------------------

    @classmethod
    def register(
        cls,
        member_id: MemberId,
        user_id: UserId,
        name: str,
        email: str,
        point_account: PointAccount,
    ) -> Member:
        return cls(
            member_id=member_id,
            user_id=user_id,
            name=name,
            email=email,
            _point_account=point_account,
        )

    # ------------------------------------------------------------------
    # 읽기 전용 프로퍼티
    # ------------------------------------------------------------------

    @property
    def point_account(self) -> PointAccount:
        """PointAccount 읽기 전용 접근."""
        return self._point_account

    @property
    def grade(self) -> MemberGrade:
        return self._point_account.grade

    @property
    def point_balance(self) -> Money:
        return self._point_account.balance

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    def apply_payment(self, order_id: OrderId, paid_amount: Money, now: datetime = None) -> None:
        """결제 완료 처리 — 포인트 적립 후 등급 승급 확인."""
        self._point_account.earn(self.member_id, order_id, paid_amount, now)
        self._point_account.promote_if_eligible(self.member_id, now)

    def spend_points(self, amount: Money) -> None:
        """포인트 사용. 내부적으로 PointAccount.redeem() 위임."""
        self._point_account.redeem(amount)

    def pull_domain_events(self) -> List[DomainEvent]:
        """발행 대기 중인 모든 도메인 이벤트(Member 루트 + PointAccount)를 반환하고 비운다."""
        account_events = self._point_account.pull_pending_events()
        root_events = list(self._pending_events)
        self._pending_events.clear()
        return root_events + account_events
