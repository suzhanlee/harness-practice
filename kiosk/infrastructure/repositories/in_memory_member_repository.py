from typing import Dict, Optional

from ...domain.models.member import Member
from ...domain.models.value_objects import MemberId, UserId
from ...domain.repositories.member_repository import MemberRepository


class InMemoryMemberRepository(MemberRepository):
    def __init__(self):
        self._store: Dict[MemberId, Member] = {}

    def save(self, member: Member) -> None:
        self._store[member.member_id] = member

    def find_by_id(self, member_id: MemberId) -> Optional[Member]:
        return self._store.get(member_id)

    def find_by_user_id(self, user_id: UserId) -> Optional[Member]:
        for member in self._store.values():
            if member.user_id == user_id:
                return member
        return None
