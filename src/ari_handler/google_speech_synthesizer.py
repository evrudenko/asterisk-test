import asyncio
import io

from audio_converter import AudioConverter
from gtts import gTTS
from speech_synthesizer import SpeechSynthesizer


class GoogleSpeechSynthesizer(SpeechSynthesizer):
    """Google Speech Synthesizer."""

    def _synthesize_sync(self, text: str) -> bytes:
        """
        Synthesize text to audio using Google Speech Synthesizer.
        """
        tts = gTTS(text, lang="ru")
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        return buffer.getvalue()

    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize text to audio using Google Speech Synthesizer.
        """
        synthesized = await asyncio.to_thread(self._synthesize_sync, text)
        return await AudioConverter.mp3_to_ulaw(synthesized)
