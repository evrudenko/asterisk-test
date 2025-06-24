from typing import Optional

from pydantic import BaseModel, field_validator

from .channel import Channel
from .event_type import EventType


class Event(BaseModel):
    """Base class for ARI events."""

    type: EventType
    timestamp: str
    channel: Optional[Channel] = None
    asterisk_id: str
    application: str

    @field_validator("type", mode="before")
    def validate_event_type(cls, value) -> EventType:
        """
        Validate and convert the event type to an EventType enum.
        Unknown event types will be set to EventType.UNKNOWN.
        """
        try:
            return EventType(value)
        except ValueError:
            return EventType.UNKNOWN
