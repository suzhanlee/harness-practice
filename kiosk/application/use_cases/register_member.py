from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ...domain.models.member import Member, PointAccount
from ...domain.models.value_objects import MemberGrade, MemberId, Money, PointAccountId, UserId
from ...domain.repositories.member_repository import MemberRepository


@dataclass
class MemberDTO:
    member_id: str
    user_id: str
    name: str
    email: str
    grade: str
    point_balance: str


class RegisterMemberUseCase:
    def __init__(self, member_repo: MemberRepository) -> None:
        self._member_repo = member_repo

    def execute(self, user_id: str, name: str, email: str) -> MemberDTO:
        uid = UserId.from_str(user_id)

        # 중복 등록 방지
        existing = self._member_repo.find_by_user_id(uid)
        if existing is not None:
            raise ValueError(f"이미 등록된 회원입니다: {user_id}")

        member_id = MemberId.generate()
        account_id = PointAccountId.generate()
        point_account = PointAccount(
            account_id=account_id,
            balance=Money(Decimal("0")),
            grade=MemberGrade.NORMAL,
            total_paid=Money(Decimal("0")),
        )
        member = Member.register(
            member_id=member_id,
            user_id=uid,
            name=name,
            email=email,
            point_account=point_account,
        )
        self._member_repo.save(member)

        return MemberDTO(
            member_id=str(member_id.value),
            user_id=str(uid.value),
            name=name,
            email=email,
            grade=member.grade.value,
            point_balance=str(member.point_balance.amount),
        )
