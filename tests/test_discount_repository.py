import pytest
from decimal import Decimal
from kiosk.infrastructure.repositories.in_memory_discount_repository import InMemoryDiscountRepository
from kiosk.domain.models.discount import Discount
from kiosk.domain.models.value_objects import DiscountId, CouponCode, DiscountRule


class TestInMemoryDiscountRepository:
    @pytest.fixture
    def repo(self):
        return InMemoryDiscountRepository()

    @pytest.fixture
    def discount(self):
        return Discount(
            DiscountId.generate(),
            CouponCode("TEST10"),
            DiscountRule("percentage", Decimal("10"), "product")
        )

    def test_save_and_find_by_id(self, repo, discount):
        repo.save(discount)
        found = repo.find_by_id(discount.id)
        assert found == discount

    def test_find_by_id_not_found(self, repo):
        not_found = repo.find_by_id(DiscountId.generate())
        assert not_found is None

    def test_find_by_code(self, repo, discount):
        repo.save(discount)
        found = repo.find_by_code(discount.code)
        assert found == discount

    def test_find_by_code_not_found(self, repo):
        not_found = repo.find_by_code(CouponCode("NOTEXIST"))
        assert not_found is None

    def test_list_active(self, repo):
        active = Discount(
            DiscountId.generate(),
            CouponCode("ACTIVE"),
            DiscountRule("fixed", Decimal("1000"), "order"),
            is_active=True
        )
        inactive = Discount(
            DiscountId.generate(),
            CouponCode("INACTIVE"),
            DiscountRule("fixed", Decimal("2000"), "order"),
            is_active=False
        )
        repo.save(active)
        repo.save(inactive)

        active_list = repo.list_active()
        assert len(active_list) == 1
        assert active_list[0] == active
