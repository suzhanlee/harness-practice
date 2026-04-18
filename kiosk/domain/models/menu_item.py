from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from .value_objects import MenuItemId, Money, DiscountRule


class MenuCategory(Enum):
    BURGER = "버거"
    DRINK = "음료"
    SIDE = "사이드"
    SET = "세트"


@dataclass
class MenuItem:
    id: MenuItemId
    name: str
    price: Money
    category: MenuCategory
    available: bool = True

    def mark_unavailable(self):
        self.available = False

    def mark_available(self):
        self.available = True

    def update_price(self, new_price: Money):
        if new_price.amount <= 0:
            raise ValueError("가격은 0보다 커야 합니다.")
        self.price = new_price

    def get_discounted_price(self, discount_rule: DiscountRule) -> Money:
        if discount_rule.discount_type == "fixed":
            discounted = max(Decimal("0"), self.price.amount - discount_rule.value)
            return Money(discounted, self.price.currency)
        elif discount_rule.discount_type == "percentage":
            discount_amount = self.price.amount * (discount_rule.value / Decimal("100"))
            discounted = self.price.amount - discount_amount
            return Money(discounted, self.price.currency)
        else:
            raise ValueError(f"알 수 없는 할인 타입: {discount_rule.discount_type}")

    @classmethod
    def create(cls, name: str, price: Money, category: MenuCategory) -> MenuItem:
        return cls(
            id=MenuItemId.generate(),
            name=name,
            price=price,
            category=category,
        )
