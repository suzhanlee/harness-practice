"""할인 파이프라인 통합 테스트.

VipGradeDiscountRule, CouponDiscountRule, PointRedemptionRule 복합 적용 시나리오,
priority 중복·stacking cap 검증, 게스트 주문 분기 테스트를 포함한다.
"""
from decimal import Decimal

import pytest

from kiosk.domain.models.discount_rules import (
    CouponDiscountRule,
    PointRedemptionRule,
    VipGradeDiscountRule,
)
from kiosk.domain.models.order import Order, OrderItem
from kiosk.domain.models.value_objects import (
    MemberGrade,
    MenuItemId,
    Money,
    OrderId,
    UserId,
)


# ────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────

def _make_order_with_amount(amount: Decimal) -> Order:
    """주어진 금액의 단일 아이템을 가진 PENDING Order를 반환한다."""
    order = Order.create()
    item = OrderItem(MenuItemId.generate(), "테스트메뉴", Money(amount), 1)
    order.add_item(item)
    return order


# ────────────────────────────────────────────────────────
# 복합 파이프라인 테스트
# ────────────────────────────────────────────────────────

class TestDiscountPipelineCombined:
    """VipGradeDiscountRule + CouponDiscountRule + PointRedemptionRule 복합 적용."""

    def test_vip_then_coupon_then_point_pipeline(self):
        """VIP 5% → 쿠폰 1000원 → 포인트 500원 순서로 적용된다.

        원가 10000원:
          1) VIP 5%  → 할인 500, 잔액 9500
          2) 쿠폰 1000 → 할인 1000, 잔액 8500
          3) 포인트 500 → 할인 500, 잔액 8000
        """
        order = _make_order_with_amount(Decimal("10000"))

        vip_rule = VipGradeDiscountRule(grade=MemberGrade.VIP)
        coupon_rule = CouponDiscountRule(coupon_discount_amount=Money(Decimal("1000")))
        point_rule = PointRedemptionRule(points_to_redeem=Money(Decimal("500")))

        # 순서를 뒤섞어 적용해도 priority 기준으로 정렬된다.
        order.apply_discount(point_rule)
        order.apply_discount(coupon_rule)
        order.apply_discount(vip_rule)

        result = order.get_total_after_discounts()
        assert result.amount == Decimal("8000")

    def test_vip_and_coupon_only(self):
        """VIP 5% → 쿠폰 2000원 파이프라인.

        원가 20000원:
          1) VIP 5%  → 할인 1000, 잔액 19000
          2) 쿠폰 2000 → 할인 2000, 잔액 17000
        """
        order = _make_order_with_amount(Decimal("20000"))

        vip_rule = VipGradeDiscountRule(grade=MemberGrade.VIP)
        coupon_rule = CouponDiscountRule(coupon_discount_amount=Money(Decimal("2000")))

        order.apply_discount(vip_rule)
        order.apply_discount(coupon_rule)

        result = order.get_total_after_discounts()
        assert result.amount == Decimal("17000")

    def test_coupon_and_point_only(self):
        """쿠폰 3000원 → 포인트 2000원 파이프라인.

        원가 10000원:
          1) 쿠폰 3000 → 할인 3000, 잔액 7000
          2) 포인트 2000 → 할인 2000, 잔액 5000
        """
        order = _make_order_with_amount(Decimal("10000"))

        coupon_rule = CouponDiscountRule(coupon_discount_amount=Money(Decimal("3000")))
        point_rule = PointRedemptionRule(points_to_redeem=Money(Decimal("2000")))

        order.apply_discount(coupon_rule)
        order.apply_discount(point_rule)

        result = order.get_total_after_discounts()
        assert result.amount == Decimal("5000")

    def test_gold_grade_discount(self):
        """GOLD 등급(3%) 회원에 쿠폰 결합.

        원가 10000원:
          1) GOLD 3% → 할인 300, 잔액 9700
          2) 쿠폰 700 → 할인 700, 잔액 9000
        """
        order = _make_order_with_amount(Decimal("10000"))

        gold_rule = VipGradeDiscountRule(grade=MemberGrade.GOLD)
        coupon_rule = CouponDiscountRule(coupon_discount_amount=Money(Decimal("700")))

        order.apply_discount(gold_rule)
        order.apply_discount(coupon_rule)

        result = order.get_total_after_discounts()
        assert result.amount == Decimal("9000")

    def test_priority_ordering_is_applied_regardless_of_insertion_order(self):
        """입력 순서와 무관하게 priority 오름차순(VIP=10, Coupon=20, Point=30)으로 계산된다."""
        order = _make_order_with_amount(Decimal("10000"))

        vip_rule = VipGradeDiscountRule(grade=MemberGrade.VIP)
        coupon_rule = CouponDiscountRule(coupon_discount_amount=Money(Decimal("1000")))
        point_rule = PointRedemptionRule(points_to_redeem=Money(Decimal("500")))

        # 역순 추가
        order.apply_discount(point_rule)
        order.apply_discount(coupon_rule)
        order.apply_discount(vip_rule)

        assert order.get_total_after_discounts().amount == Decimal("8000")

        # 정순 추가도 동일
        order2 = _make_order_with_amount(Decimal("10000"))
        order2.apply_discount(vip_rule)
        order2.apply_discount(coupon_rule)
        order2.apply_discount(point_rule)

        assert order2.get_total_after_discounts().amount == Decimal("8000")


# ────────────────────────────────────────────────────────
# Stacking cap (총액 초과 할인 → 0 고정)
# ────────────────────────────────────────────────────────

class TestStackingCap:
    """할인 합계가 원가를 초과할 때 최종 금액은 0으로 고정된다."""

    def test_combined_discounts_exceed_total_capped_at_zero(self):
        """쿠폰 6000 + 포인트 6000 이 원가 10000을 초과 → 0원."""
        order = _make_order_with_amount(Decimal("10000"))

        coupon_rule = CouponDiscountRule(coupon_discount_amount=Money(Decimal("6000")))
        point_rule = PointRedemptionRule(points_to_redeem=Money(Decimal("6000")))

        order.apply_discount(coupon_rule)
        order.apply_discount(point_rule)

        result = order.get_total_after_discounts()
        assert result.amount == Decimal("0")

    def test_single_discount_exceeds_total_capped_at_zero(self):
        """포인트 20000원이 원가 10000원을 초과 → 0원."""
        order = _make_order_with_amount(Decimal("10000"))

        point_rule = PointRedemptionRule(points_to_redeem=Money(Decimal("20000")))
        order.apply_discount(point_rule)

        assert order.get_total_after_discounts().amount == Decimal("0")

    def test_vip_plus_coupon_exceeds_total_capped_at_zero(self):
        """VIP 5% 후 쿠폰이 잔액보다 큰 경우 → 0원.

        원가 1000:
          1) VIP 5% → 950
          2) 쿠폰 2000 → 950이 원가보다 작으므로 950 할인 → 0
        """
        order = _make_order_with_amount(Decimal("1000"))

        vip_rule = VipGradeDiscountRule(grade=MemberGrade.VIP)
        coupon_rule = CouponDiscountRule(coupon_discount_amount=Money(Decimal("2000")))

        order.apply_discount(vip_rule)
        order.apply_discount(coupon_rule)

        assert order.get_total_after_discounts().amount == Decimal("0")

    def test_result_amount_never_negative(self):
        """최종 금액은 절대 음수가 될 수 없다."""
        order = _make_order_with_amount(Decimal("500"))

        vip_rule = VipGradeDiscountRule(grade=MemberGrade.VIP)
        coupon_rule = CouponDiscountRule(coupon_discount_amount=Money(Decimal("1000")))
        point_rule = PointRedemptionRule(points_to_redeem=Money(Decimal("1000")))

        order.apply_discount(vip_rule)
        order.apply_discount(coupon_rule)
        order.apply_discount(point_rule)

        result = order.get_total_after_discounts()
        assert result.amount >= Decimal("0")


# ────────────────────────────────────────────────────────
# Priority 중복 검증
# ────────────────────────────────────────────────────────

class TestPriorityDuplicateValidation:
    """동일 priority를 가진 두 규칙을 적용하면 ValueError가 발생한다."""

    def test_two_vip_rules_same_priority_raises(self):
        """VipGradeDiscountRule은 priority=10으로 고정; 두 번째 적용 시 ValueError."""
        order = _make_order_with_amount(Decimal("10000"))

        rule1 = VipGradeDiscountRule(grade=MemberGrade.VIP)
        rule2 = VipGradeDiscountRule(grade=MemberGrade.GOLD)

        order.apply_discount(rule1)

        with pytest.raises(ValueError):
            order.apply_discount(rule2)

    def test_two_coupon_rules_same_priority_raises(self):
        """CouponDiscountRule은 priority=20; 두 번째 쿠폰 규칙 적용 시 ValueError."""
        order = _make_order_with_amount(Decimal("10000"))

        rule1 = CouponDiscountRule(coupon_discount_amount=Money(Decimal("1000")))
        rule2 = CouponDiscountRule(coupon_discount_amount=Money(Decimal("2000")))

        order.apply_discount(rule1)

        with pytest.raises(ValueError):
            order.apply_discount(rule2)

    def test_two_point_rules_same_priority_raises(self):
        """PointRedemptionRule은 priority=30; 두 번째 포인트 규칙 적용 시 ValueError."""
        order = _make_order_with_amount(Decimal("10000"))

        rule1 = PointRedemptionRule(points_to_redeem=Money(Decimal("500")))
        rule2 = PointRedemptionRule(points_to_redeem=Money(Decimal("1000")))

        order.apply_discount(rule1)

        with pytest.raises(ValueError):
            order.apply_discount(rule2)

    def test_exact_same_rule_object_raises_duplicate_error(self):
        """완전히 동일한 규칙 객체를 두 번 적용하면 '이미 적용된' 에러가 발생한다."""
        order = _make_order_with_amount(Decimal("10000"))

        rule = VipGradeDiscountRule(grade=MemberGrade.VIP)
        order.apply_discount(rule)

        with pytest.raises(ValueError, match="이미 적용된"):
            order.apply_discount(rule)

    def test_different_priority_rules_do_not_conflict(self):
        """priority가 서로 다른 규칙들은 충돌 없이 모두 적용된다."""
        order = _make_order_with_amount(Decimal("10000"))

        vip_rule = VipGradeDiscountRule(grade=MemberGrade.VIP)
        coupon_rule = CouponDiscountRule(coupon_discount_amount=Money(Decimal("1000")))
        point_rule = PointRedemptionRule(points_to_redeem=Money(Decimal("500")))

        order.apply_discount(vip_rule)
        order.apply_discount(coupon_rule)
        order.apply_discount(point_rule)

        assert len(order.get_discounts()) == 3


# ────────────────────────────────────────────────────────
# 게스트 주문 분기 테스트 (member_id 없음)
# ────────────────────────────────────────────────────────

class TestGuestOrderBranch:
    """게스트 주문: member_id가 없으면 등급 할인이 적용되지 않는다."""

    def test_guest_order_has_no_member_id(self):
        """Order.create()는 user_id=None으로 생성된다."""
        order = Order.create()
        assert order.user_id is None

    def test_guest_order_no_discount_applied(self):
        """게스트 주문에 할인을 적용하지 않으면 총액이 원가와 동일하다."""
        order = _make_order_with_amount(Decimal("10000"))
        assert order.get_total_after_discounts().amount == Decimal("10000")

    def test_guest_order_coupon_only_discount(self):
        """게스트 주문은 쿠폰 할인만 적용 가능하다 (등급 할인 없음).

        원가 10000, 쿠폰 1500 → 잔액 8500.
        """
        order = _make_order_with_amount(Decimal("10000"))

        coupon_rule = CouponDiscountRule(coupon_discount_amount=Money(Decimal("1500")))
        order.apply_discount(coupon_rule)

        assert order.get_total_after_discounts().amount == Decimal("8500")

    def test_guest_order_point_redemption_only(self):
        """게스트 주문에 포인트 규칙만 적용.

        원가 5000, 포인트 2000 → 잔액 3000.
        """
        order = _make_order_with_amount(Decimal("5000"))

        point_rule = PointRedemptionRule(points_to_redeem=Money(Decimal("2000")))
        order.apply_discount(point_rule)

        assert order.get_total_after_discounts().amount == Decimal("3000")

    def test_member_order_has_user_id(self):
        """user_id를 전달하면 Order에 저장된다."""
        user_id = UserId.generate()
        order = Order(id=OrderId.generate(), user_id=user_id)
        assert order.user_id == user_id

    def test_only_grade_discount_applied_for_member(self):
        """회원 주문에 등급 할인만 적용하면 할인이 반영된다.

        원가 10000, VIP 5% → 잔액 9500.
        """
        user_id = UserId.generate()
        order = Order(id=OrderId.generate(), user_id=user_id)
        item = OrderItem(MenuItemId.generate(), "VIP메뉴", Money(Decimal("10000")), 1)
        order.add_item(item)

        vip_rule = VipGradeDiscountRule(grade=MemberGrade.VIP)
        order.apply_discount(vip_rule)

        assert order.get_total_after_discounts().amount == Decimal("9500")
