from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from .value_objects import MenuItemId, Money


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

    @classmethod
    def create(cls, name: str, price: Money, category: MenuCategory) -> MenuItem:
        return cls(
            id=MenuItemId.generate(),
            name=name,
            price=price,
            category=category,
        )
