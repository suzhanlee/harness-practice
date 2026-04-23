from dataclasses import dataclass
from kiosk.domain.models.order import OrderStatus
from kiosk.domain.models.split_payment import SplitPayment
from kiosk.domain.models.value_objects import OrderId
from kiosk.domain.repositories.order_repository import OrderRepository
from kiosk.domain.repositories.split_payment_repository import SplitPaymentRepository


@dataclass(frozen=True)
class SplitPaymentDTO:
    split_payment_id: str
    order_id: str
    target_amount: str
    is_fully_paid: bool


class CreateSplitPaymentUseCase:
    def __init__(self, order_repo: OrderRepository, split_payment_repo: SplitPaymentRepository):
        self.order_repo = order_repo
        self.split_payment_repo = split_payment_repo

    def execute(self, order_id: str) -> SplitPaymentDTO:
        order = self.order_repo.find_by_id(OrderId.from_str(order_id))
        if order is None:
            raise ValueError(f"주문을 찾을 수 없습니다: {order_id}")
        if order.status != OrderStatus.CONFIRMED:
            raise ValueError("확인된 주문에만 분할 결제를 생성할 수 있습니다.")

        split_payment = SplitPayment.create(
            order_id=order.id,
            target_amount=order.total_amount,
        )
        self.split_payment_repo.save(split_payment)

        return SplitPaymentDTO(
            split_payment_id=str(split_payment.split_payment_id.value),
            order_id=str(split_payment.order_id.value),
            target_amount=str(split_payment.target_amount.amount),
            is_fully_paid=split_payment.is_fully_paid,
        )
