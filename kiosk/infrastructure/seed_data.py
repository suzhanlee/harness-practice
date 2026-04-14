from decimal import Decimal

from ..domain.models.menu_item import MenuItem, MenuCategory
from ..domain.models.value_objects import Money
from ..domain.repositories.menu_item_repository import MenuItemRepository


def seed_menu(repo: MenuItemRepository) -> None:
    items = [
        MenuItem.create("불고기버거", Money(Decimal("5500")), MenuCategory.BURGER),
        MenuItem.create("치즈버거", Money(Decimal("4500")), MenuCategory.BURGER),
        MenuItem.create("콜라", Money(Decimal("2000")), MenuCategory.DRINK),
        MenuItem.create("사이다", Money(Decimal("2000")), MenuCategory.DRINK),
        MenuItem.create("감자튀김", Money(Decimal("3000")), MenuCategory.SIDE),
        MenuItem.create("불고기버거 세트", Money(Decimal("8000")), MenuCategory.SET),
    ]
    for item in items:
        repo.save(item)
