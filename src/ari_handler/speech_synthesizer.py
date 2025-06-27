from abc import ABC, abstractmethod


class SpeechSynthesizer(ABC):
    """
    Abstract base class for speech synthesis.

    This class defines the interface for speech synthesis.
    """

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        pass
