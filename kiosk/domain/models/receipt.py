from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple
from uuid import uuid4


@dataclass(frozen=True)
class ReceiptRecord:
    receipt_id: str
    order_id: str
    total_amount: str
    paid_at: datetime
    applied_discounts: Tuple[str, ...] = ()
    discount_breakdown: Tuple[Dict, ...] = field(default_factory=tuple)

    @classmethod
    def create(
        cls,
        order_id: str,
        total_amount: str,
        paid_at: datetime,
        applied_discounts: Tuple[str, ...] = (),
        discount_breakdown: Tuple[Dict, ...] = (),
    ) -> ReceiptRecord:
        return cls(
            receipt_id=str(uuid4()),
            order_id=order_id,
            total_amount=total_amount,
            paid_at=paid_at,
            applied_discounts=applied_discounts,
            discount_breakdown=discount_breakdown,
        )
