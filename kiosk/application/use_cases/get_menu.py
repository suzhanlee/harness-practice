from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from ...domain.models.menu_item import MenuCategory
from ...domain.repositories.menu_item_repository import MenuItemRepository


@dataclass
class MenuItemDTO:
    id: str
    name: str
    price: Decimal
    currency: str
    category: str
    available: bool


class GetMenuUseCase:
    def __init__(self, menu_item_repo: MenuItemRepository):
        self._menu_repo = menu_item_repo

    def execute(self, category: Optional[str] = None, available_only: bool = True) -> List[MenuItemDTO]:
        if available_only:
            items = self._menu_repo.find_available()
        elif category:
            cat = MenuCategory(category)
            items = self._menu_repo.find_by_category(cat)
        else:
            items = self._menu_repo.find_all()

        return [
            MenuItemDTO(
                id=str(item.id.value),
                name=item.name,
                price=item.price.amount,
                currency=item.price.currency,
                category=item.category.value,
                available=item.available,
            )
            for item in items
        ]
