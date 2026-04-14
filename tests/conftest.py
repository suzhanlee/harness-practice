import pytest
from decimal import Decimal

from kiosk.domain.models.menu_item import MenuItem, MenuCategory
from kiosk.domain.models.value_objects import Money
from kiosk.domain.services.order_domain_service import OrderDomainService
from kiosk.infrastructure.repositories.in_memory_menu_item_repository import InMemoryMenuItemRepository
from kiosk.infrastructure.repositories.in_memory_order_repository import InMemoryOrderRepository
from kiosk.infrastructure.repositories.in_memory_payment_repository import InMemoryPaymentRepository
from kiosk.infrastructure.seed_data import seed_menu


@pytest.fixture
def burger():
    return MenuItem.create("불고기버거", Money(Decimal("5500")), MenuCategory.BURGER)


@pytest.fixture
def drink():
    return MenuItem.create("콜라", Money(Decimal("2000")), MenuCategory.DRINK)


@pytest.fixture
def menu_repo():
    return InMemoryMenuItemRepository()


@pytest.fixture
def order_repo():
    return InMemoryOrderRepository()


@pytest.fixture
def payment_repo():
    return InMemoryPaymentRepository()


@pytest.fixture
def domain_service():
    return OrderDomainService()


@pytest.fixture
def seeded_menu_repo():
    repo = InMemoryMenuItemRepository()
    seed_menu(repo)
    return repo
