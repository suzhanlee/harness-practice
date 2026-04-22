import pytest
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List

from kiosk.domain.models.coupon import Coupon
from kiosk.domain.models.menu_item import MenuItem, MenuCategory
from kiosk.domain.models.value_objects import Money
from kiosk.domain.services.order_domain_service import OrderDomainService
from kiosk.infrastructure.repositories.in_memory_coupon_repository import InMemoryCouponRepository
from kiosk.infrastructure.repositories.in_memory_menu_item_repository import InMemoryMenuItemRepository
from kiosk.infrastructure.repositories.in_memory_order_repository import InMemoryOrderRepository
from kiosk.infrastructure.repositories.in_memory_payment_repository import InMemoryPaymentRepository
from kiosk.infrastructure.repositories.in_memory_receipt_repository import InMemoryReceiptRepository
from kiosk.infrastructure.repositories.in_memory_split_payment_repository import InMemorySplitPaymentRepository
from kiosk.infrastructure.seed_data import seed_menu


@dataclass
class FakeClock:
    now: datetime


@dataclass
class FakeDispatcher:
    dispatched: List = field(default_factory=list)

    def dispatch(self, event) -> None:
        self.dispatched.append(event)


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


# ──────────────────────────────────────────────
# New fixtures: clock, dispatcher, repositories
# ──────────────────────────────────────────────

@pytest.fixture
def fake_clock():
    return FakeClock(now=datetime(2026, 6, 1, 12, 0, 0))


@pytest.fixture
def fake_dispatcher():
    return FakeDispatcher()


@pytest.fixture
def coupon_repo():
    return InMemoryCouponRepository()


@pytest.fixture
def split_payment_repo():
    return InMemorySplitPaymentRepository()


@pytest.fixture
def receipt_repo():
    return InMemoryReceiptRepository()


# ──────────────────────────────────────────────
# Coupon fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def valid_coupon():
    """유효한 쿠폰: 미래 만료, 사용 횟수 여유."""
    return Coupon.create(
        code="VALID_FIXTURE",
        discount_amount=Money(Decimal("1000")),
        expires_at=datetime(2027, 1, 1),
        max_usage=10,
    )


@pytest.fixture
def expired_coupon():
    """만료된 쿠폰: expires_at이 fake_clock.now보다 과거."""
    return Coupon.create(
        code="EXPIRED_FIXTURE",
        discount_amount=Money(Decimal("1000")),
        expires_at=datetime(2025, 1, 1),
        max_usage=10,
    )


@pytest.fixture
def exhausted_coupon():
    """사용 횟수가 소진된 쿠폰: max_usage=1, usage_count=1."""
    from kiosk.domain.models.value_objects import OrderId
    coupon = Coupon.create(
        code="EXHAUSTED_FIXTURE",
        discount_amount=Money(Decimal("1000")),
        expires_at=datetime(2027, 1, 1),
        max_usage=1,
    )
    coupon.redeem(OrderId.generate(), datetime(2026, 1, 1, 0, 0, 0))
    return coupon
