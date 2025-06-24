from enum import Enum


class ChannelState(str, Enum):

    UP = "Up"
    RING = "Ring"
    UNKNOWN = "Unknown"
