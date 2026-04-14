from dataclasses import dataclass

from ...domain.models.payment import Payment, PaymentMethod
from ...domain.models.value_objects import OrderId
from ...domain.repositories.order_repository import OrderRepository
from ...domain.repositories.payment_repository import PaymentRepository
from ...domain.services.order_domain_service import OrderDomainService


@dataclass
class ProcessPaymentResult:
    payment_id: str
    order_id: str
    amount_paid: str
    method: str
    success: bool


class ProcessPaymentUseCase:
    def __init__(
        self,
        order_repo: OrderRepository,
        payment_repo: PaymentRepository,
        order_domain_service: OrderDomainService,
    ):
        self._order_repo = order_repo
        self._payment_repo = payment_repo
        self._domain_service = order_domain_service

    def execute(self, order_id: str, method: str) -> ProcessPaymentResult:
        oid = OrderId.from_str(order_id)
        order = self._order_repo.find_by_id(oid)
        if order is None:
            raise ValueError(f"주문을 찾을 수 없습니다: {order_id}")

        self._domain_service.validate_order_for_payment(order)

        payment_method = PaymentMethod(method)
        payment = Payment.create(
            order_id=order.id,
            amount=order.total_amount,
            method=payment_method,
        )

        payment.complete()
        order.mark_paid()

        self._payment_repo.save(payment)
        self._order_repo.save(order)

        return ProcessPaymentResult(
            payment_id=str(payment.id.value),
            order_id=order_id,
            amount_paid=str(order.total_amount),
            method=payment_method.value,
            success=True,
        )
