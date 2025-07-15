import asyncio
import io
import logging

from pydub import AudioSegment

logger = logging.getLogger(__name__)


class AudioConverter:
    @staticmethod
    async def ogg_opus_to_ulaw(ogg_bytes: bytes, sample_rate: int = 8000) -> bytes:
        """Convert OGG/Opus to PCM µ-law (G.711) raw audio asynchronously."""
        return await asyncio.to_thread(
            AudioConverter._ogg_opus_to_ulaw_sync, ogg_bytes, sample_rate
        )

    @staticmethod
    async def mp3_to_ulaw(mp3_bytes: bytes, sample_rate: int = 8000) -> bytes:
        """Convert MP3 to PCM µ-law (G.711) raw audio asynchronously."""
        return await asyncio.to_thread(
            AudioConverter._mp3_to_ulaw_sync, mp3_bytes, sample_rate
        )

    @staticmethod
    async def ulaw_to_wav(ulaw_bytes: bytes, sample_rate: int = 8000) -> bytes:
        """Convert PCM µ-law to WAV for debugging/listening asynchronously."""
        return await asyncio.to_thread(
            AudioConverter._ulaw_to_wav_sync, ulaw_bytes, sample_rate
        )

    @staticmethod
    async def ulaw_to_ogg_opus(ulaw_bytes: bytes, sample_rate: int = 8000) -> bytes:
        """Convert u-law to OGG/Opus (e.g., for storage or streaming) asynchronously."""
        return await asyncio.to_thread(
            AudioConverter._ulaw_to_ogg_opus_sync, ulaw_bytes, sample_rate
        )

    @staticmethod
    async def ulaw_to_pcm(ulaw_bytes: bytes, sample_rate: int = 8000) -> bytes:
        """Convert u-law (G.711) to 16-bit PCM raw bytes (Linear PCM LE) asynchronously."""
        return await asyncio.to_thread(
            AudioConverter._ulaw_to_pcm_sync, ulaw_bytes, sample_rate
        )

    @staticmethod
    def _ogg_opus_to_ulaw_sync(ogg_bytes: bytes, sample_rate: int = 8000) -> bytes:
        """Convert OGG/Opus to PCM µ-law (G.711) raw audio."""
        audio = AudioSegment.from_file(
            io.BytesIO(ogg_bytes), format="ogg", codec="opus"
        )
        ulaw_audio = (
            audio.set_frame_rate(sample_rate).set_channels(1).set_sample_width(1)
        )

        out_buffer = io.BytesIO()
        ulaw_audio.export(out_buffer, format="mulaw", codec="pcm_mulaw")
        result = out_buffer.getvalue()
        return result

    @staticmethod
    def _mp3_to_ulaw_sync(mp3_bytes: bytes, sample_rate: int = 8000) -> bytes:
        """Convert MP3 to PCM µ-law (G.711) raw audio."""
        audio = AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")

        ulaw_audio = (
            audio.set_frame_rate(sample_rate).set_channels(1).set_sample_width(1)
        )

        # Export to u-law format
        raw_fp = io.BytesIO()
        ulaw_audio.export(raw_fp, format="mulaw", codec="pcm_mulaw")
        return raw_fp.getvalue()

    @staticmethod
    def _ulaw_to_wav_sync(ulaw_bytes: bytes, sample_rate: int = 8000) -> bytes:
        """Convert PCM µ-law to WAV for debugging/listening."""
        audio = AudioSegment(
            data=ulaw_bytes,
            sample_width=1,
            frame_rate=sample_rate,
            channels=1,
        )
        out_buffer = io.BytesIO()
        audio.export(out_buffer, format="wav")
        return out_buffer.getvalue()

    @staticmethod
    def _ulaw_to_ogg_opus_sync(ulaw_bytes: bytes, sample_rate: int = 8000) -> bytes:
        """Convert u-law to OGG/Opus (e.g., for storage or streaming)."""
        audio = AudioSegment(
            data=ulaw_bytes,
            sample_width=1,
            frame_rate=sample_rate,
            channels=1,
        )
        out_buffer = io.BytesIO()
        audio.export(out_buffer, format="ogg", codec="libopus")
        return out_buffer.getvalue()

    @staticmethod
    def _ulaw_to_pcm_sync(ulaw_bytes: bytes, sample_rate: int = 8000) -> bytes:
        """Convert u-law (G.711) to 16-bit PCM raw bytes (Linear PCM LE)."""
        audio = AudioSegment(
            data=ulaw_bytes, sample_width=1, frame_rate=sample_rate, channels=1
        )
        pcm_audio = audio.set_sample_width(2)
        out_buffer = io.BytesIO()
        pcm_audio.export(out_buffer, format="raw")
        return out_buffer.getvalue()
