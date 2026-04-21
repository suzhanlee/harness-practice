from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List
from uuid import UUID, uuid4

from .value_objects import OrderId


class TicketStatus(Enum):
    RECEIVED = "접수됨"
    COOKING = "조리중"
    READY = "준비완료"
    SERVED = "서빙완료"


@dataclass(frozen=True)
class TicketId:
    value: UUID

    @classmethod
    def generate(cls) -> TicketId:
        return cls(uuid4())


@dataclass
class KitchenTicket:
    id: TicketId
    order_id: OrderId
    items: List[tuple]  # list of (name: str, quantity: int)
    status: TicketStatus = TicketStatus.RECEIVED
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(cls, order_id: OrderId, items: list) -> KitchenTicket:
        return cls(
            id=TicketId.generate(),
            order_id=order_id,
            items=list(items),
        )

    def start_cooking(self):
        if self.status != TicketStatus.RECEIVED:
            raise ValueError("접수된 티켓만 조리를 시작할 수 있습니다.")
        self.status = TicketStatus.COOKING

    def mark_ready(self):
        if self.status != TicketStatus.COOKING:
            raise ValueError("조리중인 티켓만 준비완료로 변경할 수 있습니다.")
        self.status = TicketStatus.READY

    def mark_served(self):
        if self.status != TicketStatus.READY:
            raise ValueError("준비완료 티켓만 서빙완료로 변경할 수 있습니다.")
        self.status = TicketStatus.SERVED
