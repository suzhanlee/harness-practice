from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent:
    event_id: UUID
    occurred_at: datetime

    @classmethod
    def create(cls, **kwargs) -> DomainEvent:
        return cls(event_id=uuid4(), occurred_at=datetime.now(), **kwargs)
