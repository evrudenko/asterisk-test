import asyncio
import io

from gtts import gTTS
from audio_converter import AudioConverter
from speech_synthesizer import SpeechSynthesizer


class GoogleSpeechSynthesizer(SpeechSynthesizer):
    """
    Google Speech Synthesizer.
    """

    def _synthesize_sync(self, text: str) -> bytes:
        """
        Synthesize text to audio using Google Speech Synthesizer.
        """
        tts = gTTS(text, lang="ru")
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        return AudioConverter.mp3_to_ulaw(buffer.getvalue())

    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize text to audio using Google Speech Synthesizer.
        """
        return await asyncio.to_thread(self._synthesize_sync, text)
