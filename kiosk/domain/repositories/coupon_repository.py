from abc import ABC, abstractmethod
from typing import Optional

from ..models.coupon import Coupon
from ..models.value_objects import CouponId


class DuplicateCouponCodeError(Exception):
    """동일한 코드를 가진 쿠폰이 이미 존재할 때 발생합니다."""
    pass


class CouponRepository(ABC):

    @abstractmethod
    def save(self, coupon: Coupon) -> None:
        """쿠폰을 저장합니다. 신규 쿠폰의 코드가 이미 존재하면 DuplicateCouponCodeError를 발생시킵니다."""
        pass

    @abstractmethod
    def find_by_id(self, coupon_id: CouponId) -> Optional[Coupon]:
        """ID로 쿠폰을 조회합니다. 없으면 None을 반환합니다."""
        pass

    @abstractmethod
    def find_by_code(self, code: str) -> Optional[Coupon]:
        """코드로 쿠폰을 조회합니다. 없으면 None을 반환합니다."""
        pass
