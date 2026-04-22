from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from kiosk.domain.models.coupon import (
    Coupon,
    CouponAlreadyUsedError,
    CouponExpiredError,
    CouponUsageLimitExceededError,
)
from kiosk.domain.models.value_objects import OrderId
from kiosk.domain.repositories.coupon_repository import CouponRepository
from kiosk.application.use_cases.issue_coupon import CouponDTO


class ApplyCouponUseCase:
    """쿠폰 코드를 주문에 적용(사용 처리)합니다."""

    def __init__(self, coupon_repo: CouponRepository) -> None:
        self.coupon_repo = coupon_repo

    def execute(self, order_id: str, coupon_code: str, now: str) -> CouponDTO:
        """
        Parameters
        ----------
        order_id    : 주문 UUID 문자열
        coupon_code : 쿠폰 코드 문자열
        now         : 현재 시각 ISO 8601 문자열

        Raises
        ------
        ValueError                    : 쿠폰을 찾을 수 없을 때
        CouponExpiredError             : 만료된 쿠폰 사용 시도
        CouponUsageLimitExceededError  : 사용 횟수 초과 시
        CouponAlreadyUsedError         : 같은 주문에 이미 사용된 쿠폰
        """
        coupon: Coupon | None = self.coupon_repo.find_by_code(coupon_code)
        if coupon is None:
            raise ValueError(f"쿠폰을 찾을 수 없습니다: {coupon_code}")

        order_id_vo = OrderId.from_str(order_id)
        now_dt = datetime.fromisoformat(now)

        # domain exception 전파 (CouponExpiredError, CouponUsageLimitExceededError, CouponAlreadyUsedError)
        coupon.redeem(order_id_vo, now_dt)

        # 버그 수정: coupon 상태 저장 (기존 코드에 누락되어 있었음)
        self.coupon_repo.save(coupon)

        return CouponDTO(
            coupon_id=str(coupon.id.value),
            code=coupon.code.value,
            discount_type=coupon.discount_type,
            discount_value=coupon.discount_value,
            max_usage=coupon.max_usage,
            expires_at=coupon.expires_at.isoformat(),
        )
