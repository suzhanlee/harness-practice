"""
Coupon Aggregate 테스트
- redeem 성공 상태 전이
- CouponExpiredError
- CouponUsageLimitExceededError
- CouponAlreadyUsedError
- is_usable() True
- is_usable() False (expired)
- is_usable() False (exhausted)
"""
import pytest
from datetime import datetime, timezone
from decimal import Decimal

from kiosk.domain.models.coupon import (
    Coupon,
    CouponExpiredError,
    CouponUsageLimitExceededError,
    CouponAlreadyUsedError,
    CouponRedeemed,
)
from kiosk.domain.models.value_objects import CouponId, Money, OrderId
from kiosk.domain.repositories.coupon_repository import DuplicateCouponCodeError
from kiosk.infrastructure.repositories.in_memory_coupon_repository import InMemoryCouponRepository


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

FIXED_NOW = datetime(2026, 4, 22, 12, 0, 0)
FUTURE = datetime(2026, 12, 31, 23, 59, 59)
PAST = datetime(2026, 1, 1, 0, 0, 0)


@pytest.fixture
def discount_amount():
    return Money(Decimal("1000"))


@pytest.fixture
def valid_coupon(discount_amount):
    """유효한 쿠폰 (미래 만료, 사용 횟수 여유)"""
    return Coupon.create(
        code="VALID10",
        discount_amount=discount_amount,
        expires_at=FUTURE,
        max_usage=5,
    )


@pytest.fixture
def expired_coupon(discount_amount):
    """이미 만료된 쿠폰"""
    return Coupon.create(
        code="EXPIRED",
        discount_amount=discount_amount,
        expires_at=PAST,
        max_usage=5,
    )


@pytest.fixture
def exhausted_coupon(discount_amount):
    """사용 횟수가 모두 소진된 쿠폰"""
    coupon = Coupon.create(
        code="EXHAUSTED",
        discount_amount=discount_amount,
        expires_at=FUTURE,
        max_usage=2,
    )
    order_id_1 = OrderId.generate()
    order_id_2 = OrderId.generate()
    coupon.redeem(order_id_1, FIXED_NOW)
    coupon.redeem(order_id_2, FIXED_NOW)
    return coupon


@pytest.fixture
def order_id():
    return OrderId.generate()


# ──────────────────────────────────────────────
# 1. 성공 케이스: redeem 상태 전이
# ──────────────────────────────────────────────

def test_redeem_success(valid_coupon, order_id):
    """성공적인 redeem 은 usage_count 를 1 증가시키고 order_id 를 기록한다."""
    initial_usage = valid_coupon.usage_count
    initial_version = valid_coupon.version

    valid_coupon.redeem(order_id, FIXED_NOW)

    assert valid_coupon.usage_count == initial_usage + 1
    assert order_id in valid_coupon.redeemed_order_ids
    assert valid_coupon.version == initial_version + 1


def test_redeem_appends_pending_event(valid_coupon, order_id):
    """redeem 성공 시 _pending_events 에 CouponRedeemed 이벤트가 추가된다."""
    valid_coupon.redeem(order_id, FIXED_NOW)

    assert len(valid_coupon._pending_events) == 1
    event = valid_coupon._pending_events[0]
    assert isinstance(event, CouponRedeemed)
    assert event.coupon_id == valid_coupon.id
    assert event.order_id == order_id
    assert event.occurred_at == FIXED_NOW


# ──────────────────────────────────────────────
# 2. CouponExpiredError
# ──────────────────────────────────────────────

def test_redeem_raises_expired_error(expired_coupon, order_id):
    """만료된 쿠폰 사용 시 CouponExpiredError 가 발생한다."""
    with pytest.raises(CouponExpiredError):
        expired_coupon.redeem(order_id, FIXED_NOW)


def test_redeem_raises_expired_error_at_exact_expiry(discount_amount, order_id):
    """now == expires_at 인 경우도 만료로 처리한다."""
    coupon = Coupon.create(
        code="EXACT",
        discount_amount=discount_amount,
        expires_at=FIXED_NOW,
        max_usage=5,
    )
    with pytest.raises(CouponExpiredError):
        coupon.redeem(order_id, FIXED_NOW)


# ──────────────────────────────────────────────
# 3. CouponUsageLimitExceededError
# ──────────────────────────────────────────────

def test_redeem_raises_usage_limit_exceeded(exhausted_coupon):
    """사용 횟수가 max_usage 에 도달한 쿠폰 재사용 시 CouponUsageLimitExceededError."""
    extra_order = OrderId.generate()
    with pytest.raises(CouponUsageLimitExceededError):
        exhausted_coupon.redeem(extra_order, FIXED_NOW)


# ──────────────────────────────────────────────
# 4. CouponAlreadyUsedError
# ──────────────────────────────────────────────

def test_redeem_raises_already_used_for_same_order(valid_coupon, order_id):
    """동일 order_id 로 두 번 redeem 하면 CouponAlreadyUsedError 가 발생한다."""
    valid_coupon.redeem(order_id, FIXED_NOW)
    with pytest.raises(CouponAlreadyUsedError):
        valid_coupon.redeem(order_id, FIXED_NOW)


# ──────────────────────────────────────────────
# 5. is_usable() True
# ──────────────────────────────────────────────

def test_is_usable_returns_true_for_valid_coupon(valid_coupon):
    """유효한 쿠폰은 is_usable() == True."""
    assert valid_coupon.is_usable(FIXED_NOW) is True


# ──────────────────────────────────────────────
# 6. is_usable() False — expired
# ──────────────────────────────────────────────

def test_is_usable_returns_false_for_expired_coupon(expired_coupon):
    """만료된 쿠폰은 is_usable() == False."""
    assert expired_coupon.is_usable(FIXED_NOW) is False


# ──────────────────────────────────────────────
# 7. is_usable() False — exhausted
# ──────────────────────────────────────────────

def test_is_usable_returns_false_for_exhausted_coupon(exhausted_coupon):
    """사용 횟수가 소진된 쿠폰은 is_usable() == False."""
    assert exhausted_coupon.is_usable(FIXED_NOW) is False


# ──────────────────────────────────────────────
# Repository 테스트
# ──────────────────────────────────────────────

def test_repository_save_and_find_by_id(valid_coupon):
    repo = InMemoryCouponRepository()
    repo.save(valid_coupon)
    found = repo.find_by_id(valid_coupon.id)
    assert found is valid_coupon


def test_repository_find_by_code(valid_coupon):
    repo = InMemoryCouponRepository()
    repo.save(valid_coupon)
    found = repo.find_by_code("VALID10")
    assert found is valid_coupon


def test_repository_find_by_id_returns_none_for_missing():
    repo = InMemoryCouponRepository()
    assert repo.find_by_id(CouponId.generate()) is None


def test_repository_find_by_code_returns_none_for_missing():
    repo = InMemoryCouponRepository()
    assert repo.find_by_code("NONEXISTENT") is None


def test_repository_raises_on_duplicate_code(valid_coupon, discount_amount):
    """동일 코드를 가진 신규 쿠폰 저장 시 DuplicateCouponCodeError 발생."""
    repo = InMemoryCouponRepository()
    repo.save(valid_coupon)

    duplicate = Coupon.create(
        code="VALID10",
        discount_amount=discount_amount,
        expires_at=FUTURE,
        max_usage=3,
    )
    with pytest.raises(DuplicateCouponCodeError):
        repo.save(duplicate)


def test_repository_update_existing_coupon_no_duplicate_error(valid_coupon, order_id):
    """기존 쿠폰(같은 ID)을 업데이트할 때는 코드 중복 오류가 발생하지 않는다."""
    repo = InMemoryCouponRepository()
    repo.save(valid_coupon)

    valid_coupon.redeem(order_id, FIXED_NOW)
    # 동일 ID 이므로 업데이트 — DuplicateCouponCodeError 발생 금지
    repo.save(valid_coupon)
    found = repo.find_by_id(valid_coupon.id)
    assert found.usage_count == 1
