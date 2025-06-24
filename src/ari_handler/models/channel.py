from pydantic import BaseModel, field_validator

from .caller import Caller
from .channel_state import ChannelState
from .dialplan import Dialplan


class Channel(BaseModel):
    """Represents a channel in the ARI system."""

    id: str
    name: str
    state: ChannelState
    protocol_id: str
    caller: Caller
    dialplan: Dialplan
    language: str

    @field_validator("state", mode="before")
    def validate_state(cls, value) -> ChannelState:
        """
        Validate and convert the channel state to an ChannelState enum.
        Unknown channel states will be set to ChannelState.UNKNOWN.
        """
        try:
            return ChannelState(value)
        except ValueError:
            return ChannelState.UNKNOWN
