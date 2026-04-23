from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from ...domain.models.payment import Payment, PaymentMethod
from ...domain.models.value_objects import OrderId, UserId
from ...domain.repositories.order_repository import OrderRepository
from ...domain.repositories.payment_repository import PaymentRepository
from ...domain.repositories.menu_item_repository import MenuItemRepository
from ...domain.repositories.member_repository import MemberRepository
from ...domain.services.order_domain_service import OrderDomainService
from ...domain.services.inventory_domain_service import InventoryDomainService
from ..events.dispatcher import EventDispatcher


@dataclass
class ProcessPaymentResult:
    payment_id: str
    order_id: str
    amount_paid: str
    method: str
    success: bool
    discount_breakdown: List[Dict] = field(default_factory=list)


class ProcessPaymentUseCase:
    def __init__(
        self,
        order_repo: OrderRepository,
        payment_repo: PaymentRepository,
        order_domain_service: OrderDomainService,
        inventory_service: Optional[InventoryDomainService] = None,
        menu_repo: Optional[MenuItemRepository] = None,
        member_repo: Optional[MemberRepository] = None,
        dispatcher: Optional[EventDispatcher] = None,
    ):
        self._order_repo = order_repo
        self._payment_repo = payment_repo
        self._domain_service = order_domain_service
        self._inventory_service = inventory_service
        self._menu_repo = menu_repo
        self._member_repo = member_repo
        self._dispatcher = dispatcher

    def execute(
        self,
        order_id: str,
        method: str,
        member_id: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> ProcessPaymentResult:
        oid = OrderId.from_str(order_id)
        order = self._order_repo.find_by_id(oid)
        if order is None:
            raise ValueError(f"주문을 찾을 수 없습니다: {order_id}")

        self._domain_service.validate_order_for_payment(order)

        if self._inventory_service is not None and self._menu_repo is not None:
            self._inventory_service.validate_stock_for_order(order, self._menu_repo)

        # 할인 breakdown 계산
        discount_breakdown = self._build_discount_breakdown(order)

        # 할인 후 결제 금액 계산
        final_amount = order.get_total_after_discounts()

        payment_method = PaymentMethod(method)
        payment = Payment.create(
            order_id=order.id,
            amount=final_amount,
            method=payment_method,
        )

        payment.complete()
        order.mark_paid()

        if self._inventory_service is not None and self._menu_repo is not None:
            self._inventory_service.consume_stock_for_order(order, self._menu_repo)

        self._payment_repo.save(payment)
        self._order_repo.save(order)

        # 멤버십 포인트 적립 처리
        if member_id is not None and self._member_repo is not None:
            user_id = UserId.from_str(member_id)
            member = self._member_repo.find_by_user_id(user_id)
            if member is not None:
                member.apply_payment(oid, final_amount, now)
                self._member_repo.save(member)
                domain_events = member.pull_domain_events()
                if self._dispatcher is not None and domain_events:
                    self._dispatcher.dispatch(domain_events)

        return ProcessPaymentResult(
            payment_id=str(payment.id.value),
            order_id=order_id,
            amount_paid=str(final_amount.amount),
            method=payment_method.value,
            success=True,
            discount_breakdown=discount_breakdown,
        )

    def _build_discount_breakdown(self, order) -> List[Dict]:
        """적용된 할인 규칙별 rule_name/discount_amount를 계산해 반환."""
        breakdown = []
        discounts = order.get_discounts()
        if not discounts:
            return breakdown

        running_total = order.total_amount
        for rule in sorted(discounts, key=lambda r: r.priority):
            discount_amount = rule.calculate(running_total)
            remaining = running_total.amount - discount_amount.amount
            running_total_after = running_total.__class__(
                max(Decimal("0"), remaining), running_total.currency
            )
            breakdown.append({
                "rule_name": type(rule).__name__,
                "discount_amount": str(discount_amount.amount),
            })
            running_total = running_total_after

        return breakdown
