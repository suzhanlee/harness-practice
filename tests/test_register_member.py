import pytest
from decimal import Decimal

from kiosk.application.use_cases.register_member import RegisterMemberUseCase, MemberDTO
from kiosk.infrastructure.repositories.in_memory_member_repository import InMemoryMemberRepository


@pytest.fixture
def member_repo():
    return InMemoryMemberRepository()


@pytest.fixture
def use_case(member_repo):
    return RegisterMemberUseCase(member_repo)


class TestRegisterMemberUseCase:
    def test_register_member_returns_dto(self, use_case, member_repo):
        """정상 등록 시 MemberDTO를 반환한다."""
        from uuid import UUID
        user_id = str(UUID(int=1))
        dto = use_case.execute(user_id=user_id, name="홍길동", email="hong@example.com")

        assert isinstance(dto, MemberDTO)
        assert dto.user_id == user_id
        assert dto.name == "홍길동"
        assert dto.email == "hong@example.com"
        assert dto.grade == "NORMAL"
        assert dto.point_balance == "0"
        assert dto.member_id is not None

    def test_register_member_persisted(self, use_case, member_repo):
        """등록 후 member_repo에 저장된다."""
        from uuid import UUID
        from kiosk.domain.models.value_objects import UserId

        user_id = str(UUID(int=2))
        dto = use_case.execute(user_id=user_id, name="이순신", email="lee@example.com")

        uid = UserId.from_str(user_id)
        saved = member_repo.find_by_user_id(uid)
        assert saved is not None
        assert saved.name == "이순신"

    def test_register_duplicate_user_id_raises(self, use_case):
        """동일 user_id로 두 번 등록하면 ValueError가 발생한다."""
        from uuid import UUID
        user_id = str(UUID(int=3))
        use_case.execute(user_id=user_id, name="첫번째", email="first@example.com")

        with pytest.raises(ValueError):
            use_case.execute(user_id=user_id, name="두번째", email="second@example.com")
