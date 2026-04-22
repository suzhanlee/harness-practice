from __future__ import annotations

import logging

from kiosk.domain.events.payment_events import CouponRedeemed

logger = logging.getLogger(__name__)


class LoggingAuditHandler:
    def handle(self, event: CouponRedeemed) -> None:
        logger.warning(
            "Coupon %s redeemed for order %s, discount: %s",
            event.coupon_id.value,
            event.order_id.value,
            event.discount_amount.amount,
        )
