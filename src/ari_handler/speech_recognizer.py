from abc import ABC, abstractmethod
from typing import Optional


class SpeechRecognizer(ABC):
    """
    Abstract base class for speech recognition.

    This class defines the interface for speech recognition.
    """

    @abstractmethod
    async def recognize(self, ulaw_data: bytes) -> Optional[str]:
        pass
