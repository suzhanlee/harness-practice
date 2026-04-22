"""E2E integration test: coupon issuance → apply → split payment → receipt creation."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from kiosk.application.event_handlers.logging_audit_handler import LoggingAuditHandler
from kiosk.application.event_handlers.order_settlement_handler import OrderSettlementHandler
from kiosk.application.events.dispatcher import EventDispatcher
from kiosk.application.use_cases.add_payment_attempt import AddPaymentAttemptUseCase
from kiosk.application.use_cases.apply_coupon import ApplyCouponUseCase
from kiosk.application.use_cases.cart_use_cases import AddToCartUseCase, CheckoutUseCase
from kiosk.application.use_cases.create_split_payment import CreateSplitPaymentUseCase
from kiosk.application.use_cases.issue_coupon import IssueCouponUseCase
from kiosk.domain.events.payment_events import CouponRedeemed, OrderPaid
from kiosk.domain.models.order import OrderStatus
from kiosk.domain.models.value_objects import Money, OrderId, SplitPaymentId
from kiosk.domain.models.menu_item import MenuItem, MenuCategory
from kiosk.infrastructure.repositories.in_memory_coupon_repository import InMemoryCouponRepository
from kiosk.infrastructure.repositories.in_memory_order_repository import InMemoryOrderRepository
from kiosk.infrastructure.repositories.in_memory_receipt_repository import InMemoryReceiptRepository
from kiosk.infrastructure.repositories.in_memory_split_payment_repository import InMemorySplitPaymentRepository


def _build_test_deps():
    """테스트용 의존성 컨테이너 구성."""
    order_repo = InMemoryOrderRepository()
    coupon_repo = InMemoryCouponRepository()
    split_payment_repo = InMemorySplitPaymentRepository()
    receipt_repo = InMemoryReceiptRepository()

    settlement_handler = OrderSettlementHandler(order_repo, receipt_repo)
    audit_handler = LoggingAuditHandler()

    dispatcher = EventDispatcher()
    dispatcher.register(OrderPaid, settlement_handler.handle)
    dispatcher.register(CouponRedeemed, audit_handler.handle)

    issue_coupon = IssueCouponUseCase(coupon_repo)
    apply_coupon = ApplyCouponUseCase(coupon_repo)
    add_to_cart = AddToCartUseCase(order_repo)
    checkout = CheckoutUseCase(order_repo)
    create_split_payment = CreateSplitPaymentUseCase(order_repo, split_payment_repo)
    add_payment_attempt = AddPaymentAttemptUseCase(split_payment_repo)

    return {
        "order_repo": order_repo,
        "coupon_repo": coupon_repo,
        "split_payment_repo": split_payment_repo,
        "receipt_repo": receipt_repo,
        "dispatcher": dispatcher,
        "issue_coupon": issue_coupon,
        "apply_coupon": apply_coupon,
        "add_to_cart": add_to_cart,
        "checkout": checkout,
        "create_split_payment": create_split_payment,
        "add_payment_attempt": add_payment_attempt,
    }


def _add_item_and_confirm(deps, price: str = "5500", quantity: int = 2) -> str:
    """테스트용 헬퍼: 카트에 아이템 추가 후 CONFIRMED 상태로 전환. order_id 반환."""
    menu_item_id = str(uuid.uuid4())
    cart = deps["add_to_cart"].execute(
        order_id="",
        menu_item_id=menu_item_id,
        name="테스트버거",
        unit_price_amount=price,
        quantity=quantity,
    )
    order_id_str = cart.order_id
    # CheckoutUseCase confirms the order (PENDING → CONFIRMED)
    deps["checkout"].execute(order_id_str)
    return order_id_str


class TestCouponE2EFlow:
    """Full E2E: issue coupon → cart → confirm → apply coupon → split payment → receipt."""

    def test_full_flow_discount_coupon_split_payment_receipt(self):
        """할인 적용 → 쿠폰 사용 → 분할결제 → 영수증 생성 전체 흐름 검증."""
        deps = _build_test_deps()

        # Step 1: Issue a coupon
        coupon_dto = deps["issue_coupon"].execute(
            code="E2E_FIXED_1000",
            discount_type="fixed",
            discount_value="1000",
            max_usage=5,
            expires_at="2027-12-31T23:59:59",
        )
        assert coupon_dto.code == "E2E_FIXED_1000"
        assert coupon_dto.discount_type == "fixed"

        # Step 2: Add items to cart and confirm order
        order_id_str = _add_item_and_confirm(deps, price="5500", quantity=2)
        order = deps["order_repo"].find_by_id(OrderId.from_str(order_id_str))
        assert order.status == OrderStatus.CONFIRMED

        # Step 3: Apply coupon
        coupon_result = deps["apply_coupon"].execute(
            order_id=order_id_str,
            coupon_code="E2E_FIXED_1000",
            now="2026-06-01T12:00:00",
        )
        assert coupon_result.code == "E2E_FIXED_1000"

        # Verify coupon usage_count incremented
        saved_coupon = deps["coupon_repo"].find_by_code("E2E_FIXED_1000")
        assert saved_coupon is not None
        assert saved_coupon.usage_count == 1

        # Step 4: Create split payment
        split_dto = deps["create_split_payment"].execute(order_id_str)
        assert split_dto.order_id == order_id_str
        assert split_dto.is_fully_paid is False

        # Step 5: Add payment attempt to fully pay
        result = deps["add_payment_attempt"].execute(
            split_payment_id=split_dto.split_payment_id,
            authorized_amount=split_dto.target_amount,
        )
        assert result.is_fully_paid is True
        assert result.remaining_amount == "0"

        # Step 6: Dispatch OrderPaid event → OrderSettlementHandler → verify ReceiptRecord
        event = OrderPaid(
            event_id=uuid.uuid4(),
            occurred_at=datetime.utcnow(),
            order_id=OrderId.from_str(order_id_str),
            split_payment_id=SplitPaymentId.from_str(split_dto.split_payment_id),
            total_amount=Money(Decimal(split_dto.target_amount)),
        )
        deps["dispatcher"].dispatch([event])

        # Verify ReceiptRecord created
        receipt = deps["receipt_repo"].find_by_order_id(order_id_str)
        assert receipt is not None, "영수증이 생성되어 있어야 합니다."
        assert receipt.order_id == order_id_str
        assert receipt.total_amount == split_dto.target_amount

        # Verify order is marked as PAID
        updated_order = deps["order_repo"].find_by_id(OrderId.from_str(order_id_str))
        assert updated_order.status == OrderStatus.PAID

    def test_issue_coupon_and_find_by_code(self):
        """쿠폰 발급 후 코드로 조회 가능한지 검증."""
        deps = _build_test_deps()

        coupon_dto = deps["issue_coupon"].execute(
            code="FIND_TEST",
            discount_type="percentage",
            discount_value="10",
            max_usage=3,
            expires_at="2027-01-01T00:00:00",
        )
        assert coupon_dto.coupon_id is not None

        found = deps["coupon_repo"].find_by_code("FIND_TEST")
        assert found is not None
        assert found.discount_type == "percentage"
        assert found.max_usage == 3

    def test_split_payment_multiple_attempts(self):
        """분할결제: 여러 번 나눠 결제해도 최종 완납 처리 검증."""
        deps = _build_test_deps()

        # total = 5500 * 2 = 11000, pay in two halves (5500 each)
        order_id_str = _add_item_and_confirm(deps, price="5500", quantity=2)
        split_dto = deps["create_split_payment"].execute(order_id_str)

        result1 = deps["add_payment_attempt"].execute(
            split_payment_id=split_dto.split_payment_id,
            authorized_amount="5500",
        )
        assert result1.is_fully_paid is False

        result2 = deps["add_payment_attempt"].execute(
            split_payment_id=split_dto.split_payment_id,
            authorized_amount="5500",
        )
        assert result2.is_fully_paid is True
        assert result2.remaining_amount == "0"

    def test_apply_coupon_registers_usage(self):
        """쿠폰 적용 후 사용 횟수 증가 검증."""
        deps = _build_test_deps()

        deps["issue_coupon"].execute(
            code="USAGE_COUNT_TEST",
            discount_type="fixed",
            discount_value="500",
            max_usage=2,
            expires_at="2027-06-01T00:00:00",
        )

        order_id_str = _add_item_and_confirm(deps)

        deps["apply_coupon"].execute(
            order_id=order_id_str,
            coupon_code="USAGE_COUNT_TEST",
            now="2026-06-01T00:00:00",
        )

        saved_coupon = deps["coupon_repo"].find_by_code("USAGE_COUNT_TEST")
        assert saved_coupon.usage_count == 1

    def test_receipt_created_after_order_paid_event(self):
        """OrderPaid 이벤트 디스패치 후 영수증 레코드 생성 검증."""
        deps = _build_test_deps()

        order_id_str = _add_item_and_confirm(deps, price="3000", quantity=1)
        split_dto = deps["create_split_payment"].execute(order_id_str)
        deps["add_payment_attempt"].execute(
            split_payment_id=split_dto.split_payment_id,
            authorized_amount=split_dto.target_amount,
        )

        event = OrderPaid(
            event_id=uuid.uuid4(),
            occurred_at=datetime.utcnow(),
            order_id=OrderId.from_str(order_id_str),
            split_payment_id=SplitPaymentId.from_str(split_dto.split_payment_id),
            total_amount=Money(Decimal(split_dto.target_amount)),
        )
        deps["dispatcher"].dispatch([event])

        receipt = deps["receipt_repo"].find_by_order_id(order_id_str)
        assert receipt is not None
        assert receipt.receipt_id is not None
        assert receipt.paid_at is not None
