from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from .value_objects import MenuItemId, Money, DiscountRule, Stock


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
    stock: Stock = field(default_factory=Stock.unlimited)

    def mark_unavailable(self):
        self.available = False

    def mark_available(self):
        self.available = True

    def change_price(self, new_price: Money) -> None:
        self.price = new_price

    def update_price(self, new_price: Money):
        if new_price.amount <= 0:
            raise ValueError("가격은 0보다 커야 합니다.")
        self.price = new_price

    def has_enough_stock(self, qty: int) -> bool:
        return self.stock.has_enough(qty)

    def set_stock(self, n: int) -> None:
        self.stock = Stock(n)

    def decrease_stock(self, qty: int) -> None:
        self.stock.decrease(qty)
        if not self.stock.is_unlimited() and self.stock.value == 0:
            self.available = False

    def restock(self, qty: int) -> None:
        self.stock.restock(qty)
        if not self.available:
            self.available = True

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
