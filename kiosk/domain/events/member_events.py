from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from .base import DomainEvent
from kiosk.domain.models.value_objects import MemberGrade, MemberId, Money, OrderId


@dataclass(frozen=True)
class PointsEarned(DomainEvent):
    member_id: MemberId
    order_id: OrderId
    points_earned: Money
    new_balance: Money

    @classmethod
    def create(
        cls,
        member_id: MemberId,
        order_id: OrderId,
        points_earned: Money,
        new_balance: Money,
        occurred_at: datetime = None,
    ) -> PointsEarned:
        return cls(
            event_id=uuid4(),
            occurred_at=occurred_at or datetime.now(),
            member_id=member_id,
            order_id=order_id,
            points_earned=points_earned,
            new_balance=new_balance,
        )


@dataclass(frozen=True)
class GradeUpgraded(DomainEvent):
    member_id: MemberId
    old_grade: MemberGrade
    new_grade: MemberGrade

    @classmethod
    def create(
        cls,
        member_id: MemberId,
        old_grade: MemberGrade,
        new_grade: MemberGrade,
        occurred_at: datetime = None,
    ) -> GradeUpgraded:
        return cls(
            event_id=uuid4(),
            occurred_at=occurred_at or datetime.now(),
            member_id=member_id,
            old_grade=old_grade,
            new_grade=new_grade,
        )
