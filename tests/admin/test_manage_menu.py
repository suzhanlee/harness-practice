import pytest
from decimal import Decimal

from kiosk.application.admin.manage_menu import (
    AddMenuItemUseCase,
    UpdateMenuItemUseCase,
    DeleteMenuItemUseCase,
)
from kiosk.infrastructure.repositories.in_memory_menu_item_repository import InMemoryMenuItemRepository


@pytest.fixture
def menu_repo():
    return InMemoryMenuItemRepository()


class TestAddMenuItemUseCase:
    def test_add_menu_item(self, menu_repo):
        use_case = AddMenuItemUseCase(menu_repo)
        dto = use_case.execute("새버거", Decimal("8000"), "버거")
        assert dto.name == "새버거"
        assert dto.price == Decimal("8000")
        assert dto.category == "버거"
        assert dto.available is True

    def test_add_menu_item_persisted(self, menu_repo):
        use_case = AddMenuItemUseCase(menu_repo)
        dto = use_case.execute("새버거", Decimal("8000"), "버거")
        assert menu_repo.find_by_id(__import__('kiosk.domain.models.value_objects', fromlist=['MenuItemId']).MenuItemId.from_str(dto.id)) is not None

    def test_add_invalid_category_raises(self, menu_repo):
        use_case = AddMenuItemUseCase(menu_repo)
        with pytest.raises(ValueError):
            use_case.execute("테스트", Decimal("1000"), "없는카테고리")


class TestUpdateMenuItemUseCase:
    def test_update_name(self, menu_repo):
        add = AddMenuItemUseCase(menu_repo)
        dto = add.execute("버거", Decimal("5000"), "버거")
        update = UpdateMenuItemUseCase(menu_repo)
        updated = update.execute(dto.id, name="신버거")
        assert updated.name == "신버거"
        assert updated.price == Decimal("5000")

    def test_update_price(self, menu_repo):
        add = AddMenuItemUseCase(menu_repo)
        dto = add.execute("버거", Decimal("5000"), "버거")
        update = UpdateMenuItemUseCase(menu_repo)
        updated = update.execute(dto.id, price=Decimal("6000"))
        assert updated.price == Decimal("6000")

    def test_update_not_found_raises(self, menu_repo):
        import uuid
        update = UpdateMenuItemUseCase(menu_repo)
        with pytest.raises(ValueError, match="찾을 수 없습니다"):
            update.execute(str(uuid.uuid4()), name="없음")


class TestDeleteMenuItemUseCase:
    def test_delete_menu_item(self, menu_repo):
        add = AddMenuItemUseCase(menu_repo)
        dto = add.execute("버거", Decimal("5000"), "버거")
        delete = DeleteMenuItemUseCase(menu_repo)
        deleted_id = delete.execute(dto.id)
        assert deleted_id == dto.id
        from kiosk.domain.models.value_objects import MenuItemId
        assert menu_repo.find_by_id(MenuItemId.from_str(dto.id)) is None

    def test_delete_not_found_raises(self, menu_repo):
        import uuid
        delete = DeleteMenuItemUseCase(menu_repo)
        with pytest.raises(ValueError, match="찾을 수 없습니다"):
            delete.execute(str(uuid.uuid4()))
