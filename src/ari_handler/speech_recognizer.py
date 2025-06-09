import audioop
import json
import logging
import os

from vosk import KaldiRecognizer, Model

logger = logging.getLogger(__name__)


class SpeechRecognizer:
    """
    SpeechRecognizer is a class for recognizing speech from audio data using the Vosk speech recognition library.
    It converts u-law encoded audio data to PCM format and recognizes speech in Russian.
    This class requires the Vosk model to be downloaded and placed in the specified directory.
    """

    def __init__(self, model_path="vosk-model-small-ru-0.22"):
        """
        Initializes the SpeechRecognizer with the specified Vosk model path.

        :param model_path: Path to the Vosk model directory. Default is 'vosk-model-small-ru-0.22'.
        :raises
            FileNotFoundError: If the model directory does not exist.
        """
        if not os.path.exists(model_path):
            logger.error(
                "Model not found at %s. Please download it from https://alphacephei.com/vosk/models and place it in the current directory.",
            )
            raise FileNotFoundError(f"Model directory '{model_path}' does not exist.")

        model = Model(model_path)
        self._recognizer = KaldiRecognizer(model, 16000)

    def recognize(self, ulaw_data: bytes) -> str:
        """
        Recognizes speech from the given u-law audio data.

        :param audio_data: Audio data in u-law format.
        :return: Recognized text.
        """
        pcm_audio_8k = audioop.ulaw2lin(ulaw_data, 2)
        pcm_audio_16k, _ = audioop.ratecv(pcm_audio_8k, 2, 1, 8000, 16000, None)

        if self._recognizer.AcceptWaveform(pcm_audio_16k):
            result = self._recognizer.Result()
        else:
            result = self._recognizer.FinalResult()

        return json.loads(result).get("text", "")
