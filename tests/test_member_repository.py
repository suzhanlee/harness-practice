from decimal import Decimal

import pytest

from kiosk.domain.models.member import Member, PointAccount
from kiosk.domain.models.value_objects import (
    MemberGrade,
    MemberId,
    Money,
    PointAccountId,
    UserId,
)
from kiosk.infrastructure.repositories.in_memory_member_repository import (
    InMemoryMemberRepository,
)


def _make_member(name: str = "홍길동", email: str = "hong@test.com") -> Member:
    member_id = MemberId.generate()
    user_id = UserId.generate()
    point_account = PointAccount(
        account_id=PointAccountId.generate(),
        balance=Money(Decimal("0")),
        grade=MemberGrade.NORMAL,
        total_paid=Money(Decimal("0")),
    )
    return Member.register(
        member_id=member_id,
        user_id=user_id,
        name=name,
        email=email,
        point_account=point_account,
    )


class TestInMemoryMemberRepository:

    def test_save_and_find_by_id(self):
        repo = InMemoryMemberRepository()
        member = _make_member()

        repo.save(member)
        found = repo.find_by_id(member.member_id)

        assert found is not None
        assert found.member_id == member.member_id
        assert found.name == "홍길동"

    def test_find_by_id_returns_none_when_not_found(self):
        repo = InMemoryMemberRepository()
        unknown_id = MemberId.generate()

        result = repo.find_by_id(unknown_id)

        assert result is None

    def test_find_by_user_id(self):
        repo = InMemoryMemberRepository()
        member = _make_member()

        repo.save(member)
        found = repo.find_by_user_id(member.user_id)

        assert found is not None
        assert found.user_id == member.user_id

    def test_find_by_user_id_returns_none_when_not_found(self):
        repo = InMemoryMemberRepository()
        unknown_user_id = UserId.generate()

        result = repo.find_by_user_id(unknown_user_id)

        assert result is None

    def test_save_overwrites_existing(self):
        """동일 MemberId로 두 번 저장하면 마지막 값이 유지된다."""
        repo = InMemoryMemberRepository()
        member = _make_member(name="홍길동")

        repo.save(member)

        # 이름을 직접 변경할 수 없으므로 새로운 Member 객체로 동일 ID 덮어쓰기 시뮬레이션
        member2 = Member.register(
            member_id=member.member_id,
            user_id=member.user_id,
            name="김철수",
            email="kim@test.com",
            point_account=PointAccount(
                account_id=PointAccountId.generate(),
                balance=Money(Decimal("0")),
                grade=MemberGrade.NORMAL,
                total_paid=Money(Decimal("0")),
            ),
        )
        repo.save(member2)

        found = repo.find_by_id(member.member_id)
        assert found.name == "김철수"

    def test_find_by_user_id_returns_correct_member_among_multiple(self):
        """여러 회원 중 user_id로 정확한 회원을 찾는다."""
        repo = InMemoryMemberRepository()
        member_a = _make_member(name="회원A", email="a@test.com")
        member_b = _make_member(name="회원B", email="b@test.com")

        repo.save(member_a)
        repo.save(member_b)

        found = repo.find_by_user_id(member_b.user_id)
        assert found.name == "회원B"
