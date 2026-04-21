from __future__ import annotations
from dataclasses import dataclass
from typing import List

from kiosk.domain.models.value_objects import OrderId
from kiosk.domain.repositories.order_repository import OrderRepository
from kiosk.application.events.dispatcher import EventDispatcher


@dataclass
class OrderItemDTO:
    name: str
    quantity: int
    unit_price: str
    subtotal: str


@dataclass
class OrderDTO:
    order_id: str
    status: str
    items: List[OrderItemDTO]
    total_amount: str


class ConfirmOrderUseCase:
    def __init__(self, order_repo: OrderRepository, dispatcher: EventDispatcher):
        self._order_repo = order_repo
        self._dispatcher = dispatcher

    def execute(self, order_id: str) -> OrderDTO:
        order = self._order_repo.find_by_id(OrderId.from_str(order_id))
        if order is None:
            raise ValueError(f"주문을 찾을 수 없습니다: {order_id}")
        order.confirm()
        self._order_repo.save(order)
        events = order.pull_domain_events()
        self._dispatcher.dispatch(events)
        return OrderDTO(
            order_id=str(order.id.value),
            status=order.status.value,
            items=[
                OrderItemDTO(
                    name=item.name,
                    quantity=item.quantity,
                    unit_price=str(item.unit_price.amount),
                    subtotal=str(item.subtotal.amount),
                )
                for item in order.items
            ],
            total_amount=str(order.total_amount.amount),
        )
