"""In-process asynchronous event fan-out; not a durable broker."""
import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

@dataclass(frozen=True, slots=True)
class DomainEvent:
    name: str
    occurred_at: datetime
    attributes: dict[str, Any]

Handler = Callable[[DomainEvent], Awaitable[None]]

class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: Handler) -> None:
        self._handlers[event_name].append(handler)

    async def publish(self, event_name: str, **attributes: Any) -> None:
        event = DomainEvent(event_name, datetime.now(UTC), attributes)
        handlers = tuple(self._handlers.get(event_name, ()))
        if handlers:
            await asyncio.gather(*(handler(event) for handler in handlers), return_exceptions=True)
