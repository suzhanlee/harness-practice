import pytest
from decimal import Decimal

from kiosk.domain.models.value_objects import Money, MenuItemId, OrderId, PaymentId


class TestMoney:
    def test_create_money(self):
        m = Money(Decimal("5000"))
        assert m.amount == Decimal("5000")
        assert m.currency == "KRW"

    def test_money_negative_raises(self):
        with pytest.raises(ValueError, match="0 이상"):
            Money(Decimal("-1"))

    def test_money_zero_allowed(self):
        m = Money(Decimal("0"))
        assert m.amount == Decimal("0")

    def test_money_add(self):
        a = Money(Decimal("3000"))
        b = Money(Decimal("2000"))
        result = a + b
        assert result.amount == Decimal("5000")
        assert result.currency == "KRW"

    def test_money_add_different_currency_raises(self):
        a = Money(Decimal("3000"), "KRW")
        b = Money(Decimal("2000"), "USD")
        with pytest.raises(ValueError, match="통화"):
            a + b

    def test_money_multiply(self):
        m = Money(Decimal("2000"))
        result = m * 3
        assert result.amount == Decimal("6000")

    def test_money_immutable(self):
        m = Money(Decimal("5000"))
        with pytest.raises(Exception):
            m.amount = Decimal("9999")


class TestMenuItemId:
    def test_generate_unique(self):
        id1 = MenuItemId.generate()
        id2 = MenuItemId.generate()
        assert id1 != id2

    def test_from_str(self):
        id1 = MenuItemId.generate()
        id2 = MenuItemId.from_str(str(id1.value))
        assert id1 == id2


class TestOrderId:
    def test_generate_unique(self):
        id1 = OrderId.generate()
        id2 = OrderId.generate()
        assert id1 != id2

    def test_from_str(self):
        id1 = OrderId.generate()
        id2 = OrderId.from_str(str(id1.value))
        assert id1 == id2
