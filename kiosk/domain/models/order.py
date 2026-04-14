from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from .value_objects import OrderId, MenuItemId, Money


class OrderStatus(Enum):
    PENDING = "대기중"
    CONFIRMED = "확인됨"
    PAID = "결제완료"
    CANCELLED = "취소됨"


@dataclass(frozen=True)
class OrderItem:
    menu_item_id: MenuItemId
    name: str
    unit_price: Money
    quantity: int

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("수량은 1 이상이어야 합니다.")

    @property
    def subtotal(self) -> Money:
        return self.unit_price * self.quantity


@dataclass
class Order:
    id: OrderId
    items: List[OrderItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING

    @classmethod
    def create(cls) -> Order:
        return cls(id=OrderId.generate())

    def add_item(self, item: OrderItem):
        if self.status != OrderStatus.PENDING:
            raise ValueError("대기중 상태에서만 주문 항목을 추가할 수 있습니다.")
        for existing in self.items:
            if existing.menu_item_id == item.menu_item_id:
                raise ValueError(f"이미 추가된 메뉴입니다: {item.name}. 수량 변경을 사용하세요.")
        self.items.append(item)

    def remove_item(self, menu_item_id: MenuItemId):
        if self.status != OrderStatus.PENDING:
            raise ValueError("대기중 상태에서만 주문 항목을 제거할 수 있습니다.")
        self.items = [i for i in self.items if i.menu_item_id != menu_item_id]

    def confirm(self):
        if self.status != OrderStatus.PENDING:
            raise ValueError("대기중 상태의 주문만 확인할 수 있습니다.")
        if not self.items:
            raise ValueError("주문 항목이 없습니다.")
        self.status = OrderStatus.CONFIRMED

    def mark_paid(self):
        if self.status != OrderStatus.CONFIRMED:
            raise ValueError("확인된 주문만 결제 완료로 변경할 수 있습니다.")
        self.status = OrderStatus.PAID

    def cancel(self):
        if self.status == OrderStatus.PAID:
            raise ValueError("결제 완료된 주문은 취소할 수 없습니다.")
        self.status = OrderStatus.CANCELLED

    @property
    def total_amount(self) -> Money:
        if not self.items:
            return Money(Decimal("0"))
        total = self.items[0].subtotal
        for item in self.items[1:]:
            total = total + item.subtotal
        return total

    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)
