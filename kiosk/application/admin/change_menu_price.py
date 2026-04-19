from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal

from kiosk.domain.models.value_objects import MenuItemId, Money
from kiosk.domain.repositories.menu_item_repository import MenuItemRepository


@dataclass(frozen=True)
class ChangePriceDTO:
    id: str
    name: str
    price: Decimal
    currency: str


class ChangeMenuPriceUseCase:
    def __init__(self, menu_repo: MenuItemRepository):
        self.menu_repo = menu_repo

    def execute(self, menu_item_id: str, new_price: Decimal) -> ChangePriceDTO:
        item = self.menu_repo.find_by_id(MenuItemId.from_str(menu_item_id))
        if not item:
            raise ValueError(f"메뉴를 찾을 수 없습니다: {menu_item_id}")
        item.change_price(Money(new_price))
        self.menu_repo.save(item)
        return ChangePriceDTO(
            id=str(item.id.value),
            name=item.name,
            price=item.price.amount,
            currency=item.price.currency,
        )
