import pytest
from decimal import Decimal

from kiosk.application.admin.change_menu_price import ChangeMenuPriceUseCase
from kiosk.application.admin.manage_menu import AddMenuItemUseCase
from kiosk.infrastructure.repositories.in_memory_menu_item_repository import InMemoryMenuItemRepository


@pytest.fixture
def menu_repo():
    return InMemoryMenuItemRepository()


@pytest.fixture
def added_item(menu_repo):
    return AddMenuItemUseCase(menu_repo).execute("버거", Decimal("5000"), "버거")


class TestChangeMenuPriceUseCase:
    def test_change_price(self, menu_repo, added_item):
        use_case = ChangeMenuPriceUseCase(menu_repo)
        dto = use_case.execute(added_item.id, Decimal("7000"))
        assert dto.price == Decimal("7000")
        assert dto.id == added_item.id

    def test_change_price_to_zero(self, menu_repo, added_item):
        use_case = ChangeMenuPriceUseCase(menu_repo)
        dto = use_case.execute(added_item.id, Decimal("0"))
        assert dto.price == Decimal("0")

    def test_change_price_persisted(self, menu_repo, added_item):
        use_case = ChangeMenuPriceUseCase(menu_repo)
        use_case.execute(added_item.id, Decimal("9000"))
        from kiosk.domain.models.value_objects import MenuItemId
        item = menu_repo.find_by_id(MenuItemId.from_str(added_item.id))
        assert item.price.amount == Decimal("9000")

    def test_change_price_not_found_raises(self, menu_repo):
        import uuid
        use_case = ChangeMenuPriceUseCase(menu_repo)
        with pytest.raises(ValueError, match="찾을 수 없습니다"):
            use_case.execute(str(uuid.uuid4()), Decimal("5000"))
