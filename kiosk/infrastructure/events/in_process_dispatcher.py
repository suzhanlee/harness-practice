from __future__ import annotations
from typing import List

from kiosk.application.events.dispatcher import EventDispatcher
from kiosk.domain.events.base import DomainEvent


class InProcessDispatcher(EventDispatcher):
    """인프라 구현체 — 동기 방식으로 등록된 핸들러에게 이벤트를 라우팅한다."""

    def dispatch(self, events: List[DomainEvent]) -> None:
        super().dispatch(events)
