from abc import ABC, abstractmethod
from typing import List, Optional
from ..models.menu_item import MenuItem, MenuCategory
from ..models.value_objects import MenuItemId


class MenuItemRepository(ABC):

    @abstractmethod
    def save(self, menu_item: MenuItem) -> None:
        pass

    @abstractmethod
    def find_by_id(self, menu_item_id: MenuItemId) -> Optional[MenuItem]:
        pass

    @abstractmethod
    def find_all(self) -> List[MenuItem]:
        pass

    @abstractmethod
    def find_by_category(self, category: MenuCategory) -> List[MenuItem]:
        pass

    @abstractmethod
    def find_available(self) -> List[MenuItem]:
        pass

    @abstractmethod
    def delete(self, menu_item_id: MenuItemId) -> None:
        pass
