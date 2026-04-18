from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from enum import Enum
from typing import List, Optional
from .value_objects import OrderId, MenuItemId, Money, DiscountId, OrderStateSnapshot, UserId
from .discount import Discount


class OrderStatus(Enum):
    PENDING = "대기중"
    CONFIRMED = "확인됨"
    PAID = "결제완료"
    CANCELLED = "취소됨"


@dataclass
class OrderItem:
    menu_item_id: MenuItemId
    name: str
    unit_price: Money
    quantity: int

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("수량은 1 이상이어야 합니다.")
        if self.quantity > 10:
            raise ValueError("수량은 최대 10개입니다.")

    def increase_quantity(self, delta: int):
        new_qty = self.quantity + delta
        if new_qty > 10:
            raise ValueError("수량은 최대 10개입니다.")
        object.__setattr__(self, 'quantity', new_qty)

    def set_quantity(self, new_quantity: int):
        if new_quantity < 1 or new_quantity > 10:
            raise ValueError("수량은 1~10 사이여야 합니다.")
        object.__setattr__(self, 'quantity', new_quantity)

    @property
    def subtotal(self) -> Money:
        return self.unit_price * self.quantity


@dataclass
class Order:
    id: OrderId
    items: List[OrderItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    user_id: Optional[UserId] = None
    _discounts: List[Discount] = field(default_factory=list, init=False)
    history: List[OrderStateSnapshot] = field(default_factory=list, init=False)

    @classmethod
    def create(cls) -> Order:
        order = cls(id=OrderId.generate())
        order._record_history()
        return order

    def _record_history(self):
        snapshot = OrderStateSnapshot(
            status=self.status.value,
            total_amount=self.total_amount,
            timestamp=datetime.now(),
            item_count=self.item_count
        )
        self.history.append(snapshot)

    def add_item(self, item: OrderItem):
        if self.status != OrderStatus.PENDING:
            raise ValueError("대기중 상태에서만 주문 항목을 추가할 수 있습니다.")
        existing = next(
            (i for i in self.items if i.menu_item_id == item.menu_item_id),
            None
        )
        if existing:
            existing.increase_quantity(item.quantity)
        else:
            self.items.append(item)

    def remove_item(self, menu_item_id: MenuItemId):
        if self.status != OrderStatus.PENDING:
            raise ValueError("대기중 상태에서만 주문 항목을 제거할 수 있습니다.")
        self.items = [i for i in self.items if i.menu_item_id != menu_item_id]

    def update_item_quantity(self, menu_item_id: MenuItemId, new_quantity: int):
        if self.status != OrderStatus.PENDING:
            raise ValueError("대기중 상태에서만 수량을 변경할 수 있습니다.")
        item = next(
            (i for i in self.items if i.menu_item_id == menu_item_id),
            None
        )
        if not item:
            raise ValueError(f"항목을 찾을 수 없습니다: {menu_item_id}")
        item.set_quantity(new_quantity)

    def confirm(self):
        if self.status != OrderStatus.PENDING:
            raise ValueError("대기중 상태의 주문만 확인할 수 있습니다.")
        if not self.items:
            raise ValueError("주문 항목이 없습니다.")
        self.status = OrderStatus.CONFIRMED
        self._record_history()

    def mark_paid(self):
        if self.status != OrderStatus.CONFIRMED:
            raise ValueError("확인된 주문만 결제 완료로 변경할 수 있습니다.")
        self.status = OrderStatus.PAID
        self._record_history()

    def cancel(self):
        if self.status == OrderStatus.PAID:
            raise ValueError("결제 완료된 주문은 취소할 수 없습니다.")
        self.status = OrderStatus.CANCELLED
        self._record_history()

    def apply_discount(self, discount: Discount):
        if self.status != OrderStatus.PENDING:
            raise ValueError("대기중 상태에서만 할인을 적용할 수 있습니다.")
        existing = next(
            (d for d in self._discounts if d.code == discount.code),
            None
        )
        if existing:
            raise ValueError(f"이미 적용된 쿠폰입니다: {discount.code.value}")
        self._discounts.append(discount)

    def remove_discount(self, discount_id: DiscountId):
        if self.status != OrderStatus.PENDING:
            raise ValueError("대기중 상태에서만 할인을 제거할 수 있습니다.")
        self._discounts = [d for d in self._discounts if d.id != discount_id]

    def get_discounts(self) -> List[Discount]:
        return self._discounts.copy()

    def get_total_after_discounts(self) -> Money:
        total = self.total_amount
        for discount in self._discounts:
            if discount.rule.discount_type == "fixed":
                total = Money(
                    max(Decimal("0"), total.amount - discount.rule.value),
                    total.currency
                )
            elif discount.rule.discount_type == "percentage":
                discount_amount = total.amount * (discount.rule.value / Decimal("100"))
                total = Money(total.amount - discount_amount, total.currency)
        return total

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
