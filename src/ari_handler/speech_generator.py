import io

from gtts import gTTS
from pydub import AudioSegment


class SpeechGenerator:
    """
    Class for generating u-law encoded speech from text using gTTS and pydub.

    This class provides a method to convert text to speech in u-law format,
    which can be used for audio streaming or storage.
    """

    def generate_speech(self, text: str) -> bytes:
        """
        Generates u-law encoded speech from the given text.

        :param text: Text to convert to speech.
        :return: Audio data in u-law format.
        """
        tts = gTTS(text, lang="ru")
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)

        # Загружаем mp3 в pydub
        audio = AudioSegment.from_file(mp3_fp, format="mp3")

        # Добавим 300 мс тишины в начало и конец
        silence = AudioSegment.silent(duration=300)  # в миллисекундах
        audio = silence + audio + silence

        # Преобразуем в u-law: 8kHz, 1 канал, 8 бит
        ulaw_audio = audio.set_frame_rate(8000).set_channels(1).set_sample_width(1)

        # Export to u-law format
        raw_fp = io.BytesIO()
        ulaw_audio.export(raw_fp, format="mulaw", codec="pcm_mulaw")
        return raw_fp.getvalue()
