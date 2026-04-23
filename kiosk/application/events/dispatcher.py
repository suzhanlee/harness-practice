from __future__ import annotations
from typing import Callable, Dict, List, Type

from kiosk.domain.events.base import DomainEvent


class EventDispatcher:
    def __init__(self):
        self._handlers: Dict[Type[DomainEvent], List[Callable]] = {}

    def register(self, event_type: Type[DomainEvent], handler: Callable) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def dispatch(self, events: List[DomainEvent]) -> None:
        for event in events:
            handlers = self._handlers.get(type(event), [])
            for handler in handlers:
                handler(event)
