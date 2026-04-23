from abc import ABC, abstractmethod
from typing import Optional

from ..models.member import Member
from ..models.value_objects import MemberId, UserId


class MemberRepository(ABC):

    @abstractmethod
    def save(self, member: Member) -> None:
        pass

    @abstractmethod
    def find_by_id(self, member_id: MemberId) -> Optional[Member]:
        pass

    @abstractmethod
    def find_by_user_id(self, user_id: UserId) -> Optional[Member]:
        pass
