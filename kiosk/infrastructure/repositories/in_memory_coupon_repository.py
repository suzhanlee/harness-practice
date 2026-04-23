from typing import Dict, Optional

from ...domain.models.coupon import Coupon
from ...domain.models.value_objects import CouponId
from ...domain.repositories.coupon_repository import CouponRepository, DuplicateCouponCodeError


class InMemoryCouponRepository(CouponRepository):
    def __init__(self):
        self._store: Dict[CouponId, Coupon] = {}

    def save(self, coupon: Coupon) -> None:
        """쿠폰을 저장합니다.

        신규 쿠폰(ID가 저장소에 없음)인 경우, 동일 코드가 이미 존재하면
        DuplicateCouponCodeError를 발생시킵니다.
        기존 쿠폰 업데이트(ID가 이미 존재)의 경우 코드 중복 검사를 건너뜁니다.
        """
        is_new = coupon.id not in self._store
        if is_new:
            for existing in self._store.values():
                if existing.code.value == coupon.code.value:
                    raise DuplicateCouponCodeError(
                        f"이미 존재하는 쿠폰 코드입니다: {coupon.code.value}"
                    )
        self._store[coupon.id] = coupon

    def find_by_id(self, coupon_id: CouponId) -> Optional[Coupon]:
        return self._store.get(coupon_id)

    def find_by_code(self, code: str) -> Optional[Coupon]:
        for coupon in self._store.values():
            if coupon.code.value == code:
                return coupon
        return None
