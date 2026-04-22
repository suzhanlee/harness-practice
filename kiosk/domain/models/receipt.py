from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Tuple
from uuid import uuid4


@dataclass(frozen=True)
class ReceiptRecord:
    receipt_id: str
    order_id: str
    total_amount: str
    paid_at: datetime
    applied_discounts: Tuple[str, ...] = ()

    @classmethod
    def create(
        cls,
        order_id: str,
        total_amount: str,
        paid_at: datetime,
        applied_discounts: Tuple[str, ...] = (),
    ) -> ReceiptRecord:
        return cls(
            receipt_id=str(uuid4()),
            order_id=order_id,
            total_amount=total_amount,
            paid_at=paid_at,
            applied_discounts=applied_discounts,
        )
