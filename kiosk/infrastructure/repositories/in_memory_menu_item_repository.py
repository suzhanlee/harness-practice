import threading
from typing import Dict, List, Optional

from ...domain.models.menu_item import MenuItem, MenuCategory
from ...domain.models.value_objects import MenuItemId
from ...domain.repositories.menu_item_repository import MenuItemRepository


class InMemoryMenuItemRepository(MenuItemRepository):
    def __init__(self):
        self._store: Dict[MenuItemId, MenuItem] = {}
        self._lock = threading.Lock()

    def save(self, menu_item: MenuItem) -> None:
        with self._lock:
            self._store[menu_item.id] = menu_item

    def find_by_id(self, menu_item_id: MenuItemId) -> Optional[MenuItem]:
        return self._store.get(menu_item_id)

    def find_all(self) -> List[MenuItem]:
        return list(self._store.values())

    def find_by_category(self, category: MenuCategory) -> List[MenuItem]:
        return [item for item in self._store.values() if item.category == category]

    def find_available(self) -> List[MenuItem]:
        return [item for item in self._store.values() if item.available]

    def delete(self, menu_item_id: MenuItemId) -> None:
        with self._lock:
            self._store.pop(menu_item_id, None)
