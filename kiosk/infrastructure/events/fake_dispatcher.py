from __future__ import annotations
from typing import List

from kiosk.application.events.dispatcher import EventDispatcher
from kiosk.domain.events.base import DomainEvent


class FakeDispatcher(EventDispatcher):
    """테스트용 EventDispatcher: dispatch된 이벤트를 received 리스트에 축적한다."""

    def __init__(self):
        super().__init__()
        self.received: List[DomainEvent] = []

    def dispatch(self, events: List[DomainEvent]) -> None:
        self.received.extend(events)
        super().dispatch(events)
