from pydub import AudioSegment
import io


class AudioConverter:
    @staticmethod
    def ogg_opus_to_ulaw(ogg_bytes: bytes, sample_rate: int = 8000) -> bytes:
        """
        Конвертирует OGG/Opus в PCM µ-law (G.711) raw-аудио.
        """
        audio = AudioSegment.from_file(io.BytesIO(ogg_bytes), format="ogg", codec="opus")
        ulaw_audio = audio.set_frame_rate(sample_rate).set_channels(1).set_sample_width(1)

        out_buffer = io.BytesIO()
        ulaw_audio.export(out_buffer, format="raw", codec="pcm_mulaw")
        return out_buffer.getvalue()

    @staticmethod
    def mp3_to_ulaw(mp3_bytes: bytes, sample_rate: int = 8000) -> bytes:
        """
        Конвертирует MP3 в PCM µ-law (G.711) raw-аудио.
        """
        audio = AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")

        ulaw_audio = audio.set_frame_rate(8000).set_channels(1).set_sample_width(1)

        # Export to u-law format
        raw_fp = io.BytesIO()
        ulaw_audio.export(raw_fp, format="mulaw", codec="pcm_mulaw")
        return raw_fp.getvalue()

    @staticmethod
    def ulaw_to_wav(ulaw_bytes: bytes, sample_rate: int = 8000) -> bytes:
        """
        Конвертирует PCM µ-law в WAV для отладки/прослушивания.
        """
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
    def ulaw_to_ogg_opus(ulaw_bytes: bytes, sample_rate: int = 8000) -> bytes:
        """
        Конвертирует u-law в OGG/Opus (например, для хранения или стриминга).
        """
        audio = AudioSegment(
            data=ulaw_bytes,
            sample_width=1,
            frame_rate=sample_rate,
            channels=1,
        )
        out_buffer = io.BytesIO()
        audio.export(out_buffer, format="ogg", codec="libopus")
        return out_buffer.getvalue()
