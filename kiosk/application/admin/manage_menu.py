from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from kiosk.domain.models.menu_item import MenuItem, MenuCategory
from kiosk.domain.models.value_objects import MenuItemId, Money
from kiosk.domain.repositories.menu_item_repository import MenuItemRepository


@dataclass(frozen=True)
class MenuItemDTO:
    id: str
    name: str
    price: Decimal
    currency: str
    category: str
    available: bool


def _to_dto(item: MenuItem) -> MenuItemDTO:
    return MenuItemDTO(
        id=str(item.id.value),
        name=item.name,
        price=item.price.amount,
        currency=item.price.currency,
        category=item.category.value,
        available=item.available,
    )


class AddMenuItemUseCase:
    def __init__(self, menu_repo: MenuItemRepository):
        self.menu_repo = menu_repo

    def execute(self, name: str, price: Decimal, category: str) -> MenuItemDTO:
        menu_category = MenuCategory(category)
        item = MenuItem.create(name, Money(price), menu_category)
        self.menu_repo.save(item)
        return _to_dto(item)


class UpdateMenuItemUseCase:
    def __init__(self, menu_repo: MenuItemRepository):
        self.menu_repo = menu_repo

    def execute(self, menu_item_id: str, name: Optional[str] = None, price: Optional[Decimal] = None) -> MenuItemDTO:
        item = self.menu_repo.find_by_id(MenuItemId.from_str(menu_item_id))
        if not item:
            raise ValueError(f"메뉴를 찾을 수 없습니다: {menu_item_id}")
        if name is not None:
            item.name = name
        if price is not None:
            item.change_price(Money(price))
        self.menu_repo.save(item)
        return _to_dto(item)


class DeleteMenuItemUseCase:
    def __init__(self, menu_repo: MenuItemRepository):
        self.menu_repo = menu_repo

    def execute(self, menu_item_id: str) -> str:
        mid = MenuItemId.from_str(menu_item_id)
        item = self.menu_repo.find_by_id(mid)
        if not item:
            raise ValueError(f"메뉴를 찾을 수 없습니다: {menu_item_id}")
        self.menu_repo.delete(mid)
        return menu_item_id
