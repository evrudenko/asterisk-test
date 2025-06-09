import asyncio
import audioop
import logging

import numpy as np
from llm_service import LLMService
from rtp_manager import RTPManager
from speech_generator import SpeechGenerator
from speech_recognizer import SpeechRecognizer

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Параметры для RTP
SAMPLE_RATE = 8000  # Частота дискретизации входящего аудио
CHANNELS = 1  # Количество каналов

# Параметры для обработки аудио
SILENCE_FRAMES_THRESHOLD = 20  # Количество кадров тишины для завершения фразы
SPEECH_FRAMES_THRESHOLD = 20  # Количество кадров речи для распозравания активной речи
SILENCE_RMS_THRESHOLD = 30  # RMS амплитуда для определения тишины


def is_silence(samples, threshold_rms=100):
    """Check if the audio samples are silent based on RMS amplitude."""
    pcm_audio_8k = audioop.ulaw2lin(samples, 2)
    amplitudes = np.frombuffer(pcm_audio_8k, dtype=np.int16).astype(np.float32)
    rms = np.sqrt(np.mean(amplitudes**2))
    # Uncomment this line to log RMS values
    # logger.info("RMS amplitude: %.2f", rms)
    return rms < threshold_rms


async def start(ip: str, port: int, llm_service: LLMService):
    logger.info("Starting RTP recognizer on %s:%s", ip, port)

    buffer = b""
    silence_frames = 0
    speech_frames = 0
    response_prefilled = False

    rtp_manager = RTPManager(ip, port)
    # TODO
    try:
        recognizer = SpeechRecognizer()
        speech_generator = SpeechGenerator()
        logger.info(f"Listening for RTP on {ip}:{port}...")
        async for ulaw_data, addr in rtp_manager.audio_channel(packet_size=2048):
            buffer += ulaw_data

            if is_silence(ulaw_data, SILENCE_RMS_THRESHOLD):
                silence_frames += 1
                speech_frames = 0
            else:
                speech_frames += 1
                silence_frames = 0

            if speech_frames >= SPEECH_FRAMES_THRESHOLD and rtp_manager.is_playing():
                logger.info("Speech detected, stopping playback.")
                rtp_manager.cancel_play()

            if silence_frames >= SILENCE_FRAMES_THRESHOLD:
                buffer = buffer[: -silence_frames * 160]
                if len(buffer) == 0:
                    buffer = b""
                    silence_frames = 0
                    continue

                logger.info(
                    f"Silence detected. Buffer size: {len(buffer)}, {len(buffer) / (SAMPLE_RATE * CHANNELS)} seconds"
                )

                # Распознаем текст из буфера
                text = recognizer.recognize(buffer)
                logger.info("Recognized text: %s", text)

                if text:
                    logger.info("Отправляем в LLM текст: %s", text)
                    response_text = llm_service.generate(text)
                    logger.info("Ответ от LLM: %s", response_text)

                    # response_text = text
                    # TODO генерировать по частям, если текст длинный
                    logger.info("Generating u-law response for Asterisk")
                    current_ulaw_response = speech_generator.generate_speech(
                        response_text
                    )

                    # For the first time we need to send silence before the response
                    # TODO вынести в метод
                    if not response_prefilled:
                        current_ulaw_response = (
                            b"\xff" * 160 * 40 + current_ulaw_response
                        )
                        response_prefilled = True

                    await rtp_manager.play(current_ulaw_response, addr)

                buffer = b""
                silence_frames = 0

    except KeyboardInterrupt:
        logger.info("Stopped by user.")
    finally:
        rtp_manager.close()


if __name__ == "__main__":
    asyncio.run(start("0.0.0.0", 10000))
