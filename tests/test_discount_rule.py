"""Tests for the ABC-based DiscountRule hierarchy: FixedDiscountRule, PercentageDiscountRule,
DiscountCalculation, and DiscountChain."""
from decimal import Decimal

import pytest

from kiosk.domain.models.value_objects import (
    AbstractDiscountRule,
    DiscountCalculation,
    DiscountChain,
    FixedDiscountRule,
    Money,
    PercentageDiscountRule,
)


class TestFixedDiscountRule:
    def test_calculate_returns_fixed_amount(self):
        rule = FixedDiscountRule(amount=Money(Decimal("5000")))
        discount = rule.calculate(Money(Decimal("20000")))
        assert discount == Money(Decimal("5000"))

    def test_calculate_capped_at_original(self):
        """Discount should not exceed the original price."""
        rule = FixedDiscountRule(amount=Money(Decimal("30000")))
        discount = rule.calculate(Money(Decimal("10000")))
        assert discount == Money(Decimal("10000"))

    def test_calculate_exact_price(self):
        rule = FixedDiscountRule(amount=Money(Decimal("10000")))
        discount = rule.calculate(Money(Decimal("10000")))
        assert discount == Money(Decimal("10000"))

    def test_is_abstract_discount_rule(self):
        rule = FixedDiscountRule(amount=Money(Decimal("1000")))
        assert isinstance(rule, AbstractDiscountRule)

    def test_frozen(self):
        rule = FixedDiscountRule(amount=Money(Decimal("1000")))
        with pytest.raises((AttributeError, TypeError)):
            rule.amount = Money(Decimal("2000"))  # type: ignore[misc]

    def test_currency_mismatch_raises(self):
        rule = FixedDiscountRule(amount=Money(Decimal("5000"), "USD"))
        with pytest.raises(ValueError):
            rule.calculate(Money(Decimal("20000"), "KRW"))


class TestPercentageDiscountRule:
    def test_calculate_ten_percent(self):
        rule = PercentageDiscountRule(percent=Decimal("10"))
        discount = rule.calculate(Money(Decimal("20000")))
        assert discount.amount == Decimal("2000.0")

    def test_calculate_twenty_percent(self):
        rule = PercentageDiscountRule(percent=Decimal("20"))
        discount = rule.calculate(Money(Decimal("15000")))
        assert discount.amount == Decimal("3000.0")

    def test_calculate_zero_percent(self):
        rule = PercentageDiscountRule(percent=Decimal("0"))
        discount = rule.calculate(Money(Decimal("10000")))
        assert discount.amount == Decimal("0")

    def test_calculate_hundred_percent(self):
        rule = PercentageDiscountRule(percent=Decimal("100"))
        discount = rule.calculate(Money(Decimal("10000")))
        assert discount.amount == Decimal("10000")

    def test_invalid_percent_over_100_raises(self):
        with pytest.raises(ValueError):
            PercentageDiscountRule(percent=Decimal("101"))

    def test_invalid_negative_percent_raises(self):
        with pytest.raises(ValueError):
            PercentageDiscountRule(percent=Decimal("-1"))

    def test_is_abstract_discount_rule(self):
        rule = PercentageDiscountRule(percent=Decimal("10"))
        assert isinstance(rule, AbstractDiscountRule)

    def test_frozen(self):
        rule = PercentageDiscountRule(percent=Decimal("10"))
        with pytest.raises((AttributeError, TypeError)):
            rule.percent = Decimal("20")  # type: ignore[misc]


class TestDiscountCalculation:
    def test_compute_normal(self):
        original = Money(Decimal("20000"))
        discount = Money(Decimal("5000"))
        calc = DiscountCalculation.compute(original, discount)
        assert calc.original == original
        assert calc.discount == discount
        assert calc.final == Money(Decimal("15000"))

    def test_compute_no_negative_final(self):
        """final should be floored at 0 when discount exceeds original."""
        original = Money(Decimal("3000"))
        discount = Money(Decimal("5000"))
        calc = DiscountCalculation.compute(original, discount)
        assert calc.final == Money(Decimal("0"))

    def test_compute_zero_discount(self):
        original = Money(Decimal("10000"))
        discount = Money(Decimal("0"))
        calc = DiscountCalculation.compute(original, discount)
        assert calc.final == original

    def test_frozen(self):
        calc = DiscountCalculation.compute(Money(Decimal("10000")), Money(Decimal("1000")))
        with pytest.raises((AttributeError, TypeError)):
            calc.final = Money(Decimal("0"))  # type: ignore[misc]


class TestDiscountChain:
    def test_percentage_then_fixed_order(self):
        """Percentage-first then fixed: percentage applies to original, fixed to remainder."""
        pct_rule = PercentageDiscountRule(percent=Decimal("10"))
        fixed_rule = FixedDiscountRule(amount=Money(Decimal("1000")))
        chain = DiscountChain(policies=(pct_rule, fixed_rule))

        result = chain.apply(Money(Decimal("20000")))

        # 10% of 20000 = 2000 discount → remainder 18000
        # fixed 1000 from 18000 → total discount = 3000, final = 17000
        assert result.final == Money(Decimal("17000"))
        assert result.discount == Money(Decimal("3000.0"))

    def test_single_fixed_rule(self):
        chain = DiscountChain(policies=(FixedDiscountRule(amount=Money(Decimal("3000"))),))
        result = chain.apply(Money(Decimal("10000")))
        assert result.final == Money(Decimal("7000"))

    def test_single_percentage_rule(self):
        chain = DiscountChain(policies=(PercentageDiscountRule(percent=Decimal("20")),))
        result = chain.apply(Money(Decimal("10000")))
        assert result.final == Money(Decimal("8000.0"))

    def test_empty_chain_no_discount(self):
        chain = DiscountChain(policies=())
        result = chain.apply(Money(Decimal("10000")))
        assert result.final == Money(Decimal("10000"))
        assert result.discount == Money(Decimal("0"))

    def test_negative_floor_protection(self):
        """Total discounts exceeding the price should floor final at 0."""
        pct_rule = PercentageDiscountRule(percent=Decimal("50"))
        fixed_rule = FixedDiscountRule(amount=Money(Decimal("8000")))
        chain = DiscountChain(policies=(pct_rule, fixed_rule))

        result = chain.apply(Money(Decimal("10000")))

        # 50% of 10000 = 5000 discount → remainder 5000
        # fixed 5000 (capped at 5000) → remainder 0, total discount = 10000
        assert result.final == Money(Decimal("0"))

    def test_polymorphic_dispatch(self):
        """Rules are dispatched polymorphically through AbstractDiscountRule.calculate()."""
        rules: list[AbstractDiscountRule] = [
            PercentageDiscountRule(percent=Decimal("10")),
            FixedDiscountRule(amount=Money(Decimal("500"))),
        ]
        chain = DiscountChain(policies=tuple(rules))
        result = chain.apply(Money(Decimal("5000")))
        # 10% of 5000 = 500, remainder 4500; fixed 500 from 4500 → total discount 1000, final 4000
        assert result.final == Money(Decimal("4000.0"))

    def test_frozen(self):
        chain = DiscountChain(policies=())
        with pytest.raises((AttributeError, TypeError)):
            chain.policies = (FixedDiscountRule(amount=Money(Decimal("1000"))),)  # type: ignore[misc]
