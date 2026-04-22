from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from kiosk.domain.models.coupon import Coupon
from kiosk.domain.models.value_objects import Money
from kiosk.domain.repositories.coupon_repository import CouponRepository


@dataclass(frozen=True)
class CouponDTO:
    coupon_id: str
    code: str
    discount_type: str
    discount_value: str
    max_usage: int
    expires_at: str


class IssueCouponUseCase:
    """새 쿠폰을 발급하고 저장합니다."""

    def __init__(self, coupon_repo: CouponRepository) -> None:
        self.coupon_repo = coupon_repo

    def execute(
        self,
        code: str,
        discount_type: str,
        discount_value: str,
        max_usage: int,
        expires_at: str,
    ) -> CouponDTO:
        """
        Parameters
        ----------
        code          : 쿠폰 코드 문자열
        discount_type : "fixed" 또는 "percentage"
        discount_value: Decimal-호환 문자열 (예: "1000", "10")
        max_usage     : 최대 사용 횟수
        expires_at    : ISO 8601 datetime 문자열 (예: "2026-12-31T23:59:59")
        """
        if discount_type not in ("fixed", "percentage"):
            raise ValueError(
                f"discount_type은 'fixed' 또는 'percentage'여야 합니다: {discount_type}"
            )

        value = Decimal(discount_value)
        expires_dt = datetime.fromisoformat(expires_at)

        # discount_amount: fixed이면 실제 금액, percentage이면 퍼센트 값을 Money로 래핑
        discount_amount = Money(value)

        coupon = Coupon.create(
            code=code,
            discount_amount=discount_amount,
            expires_at=expires_dt,
            max_usage=max_usage,
            discount_type=discount_type,
            discount_value=discount_value,
        )
        self.coupon_repo.save(coupon)

        return CouponDTO(
            coupon_id=str(coupon.id.value),
            code=code,
            discount_type=discount_type,
            discount_value=discount_value,
            max_usage=max_usage,
            expires_at=expires_at,
        )
