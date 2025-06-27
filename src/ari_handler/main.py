import asyncio
import audioop
import logging
import re
from dataclasses import dataclass

import numpy as np
from call_manager import CallManager
from llm_service import LLMService
from speech_synthesizer import SpeechSynthesizer
from google_speech_synthesizer import GoogleSpeechSynthesizer
from yandex_speech_synthesizer import YandexSpeechSynthesizer
from yandex_credentials_provider import YandexCredentialsProvider
from yandex_settings import YandexSettings
from speech_recognizer import SpeechRecognizer

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

lock = asyncio.Lock()

# Параметры для RTP
SAMPLE_RATE = 8000  # Частота дискретизации входящего аудио
CHANNELS = 1  # Количество каналов

# Параметры для обработки аудио
SILENCE_FRAMES_THRESHOLD = 20  # Количество кадров тишины для завершения фразы
SPEECH_FRAMES_THRESHOLD = 10  # Количество кадров речи для распозравания активной речи
SILENCE_RMS_THRESHOLD = 30  # RMS амплитуда для определения тишины


@dataclass
class ResponseChunk:
    """Data class to represent a chunk of response text."""

    text: str
    addr: tuple[str, int]


def is_silence(samples, threshold_rms=100):
    """Check if the audio samples are silent based on RMS amplitude."""
    pcm_audio_8k = audioop.ulaw2lin(samples, 2)
    amplitudes = np.frombuffer(pcm_audio_8k, dtype=np.int16).astype(np.float32)
    rms = np.sqrt(np.mean(amplitudes**2))
    # Uncomment this line to log RMS values
    # logger.info("RMS amplitude: %.2f", rms)
    return rms < threshold_rms


def split_text(text):
    """Разбивает текст на части, не превышающие max_len, по предложениям."""
    return [
        sentence.strip()
        for sentence in re.split(
            r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!|\n|\xa0)\s", text
        )
        if sentence.strip()
    ]


async def generate_speech_and_play(
    chunk: ResponseChunk,
    call_manager: CallManager,
    speech_synthesizer: SpeechSynthesizer,
    response_prefilled: bool,
):
    # Generate u-law response for the text
    logger.info("Generating u-law response for text: %s", chunk.text)
    ulaw_response = await speech_synthesizer.synthesize(chunk.text)

    # For the first time we need to send silence before the response
    if not response_prefilled:
        ulaw_response = b"\xff" * 160 * 40 + ulaw_response

    # Play the generated response
    await call_manager.play_next(ulaw_response, chunk.addr, frame_duration_ms=20)

    logger.info("Playing response scheduled for chunk: %s", chunk)


async def _empty_queue(queue: asyncio.Queue):
    """Empties the given asyncio queue by consuming all items without processing them."""
    while not queue.empty():
        queue.get_nowait()
        queue.task_done()
    logger.info("Queue emptied.")


async def _response_queue_worker(
    response_queue: asyncio.Queue,
    call_manager: CallManager,
    speech_synthesizer: SpeechSynthesizer,
):
    """Worker to process responses from the queue."""
    response_prefilled = False
    while True:
        if response_queue.empty():
            # logger.info("Response queue is empty, waiting for new responses...")
            await asyncio.sleep(1)
            continue
        try:
            logger.info("Fetching response chunk from queue...")
            async with lock:
                chunk = response_queue.get_nowait()
                logger.info("Planning to play response: %s", chunk.text)
                await generate_speech_and_play(
                    chunk,
                    call_manager,
                    speech_synthesizer,
                    response_prefilled=response_prefilled,
                )
                response_prefilled = True
                response_queue.task_done()
        except asyncio.QueueEmpty:
            continue


async def start(
    ip: str, port: int, llm_service: LLMService, speech_recognizer: SpeechRecognizer
):
    logger.info("Starting RTP recognizer on %s:%s", ip, port)

    buffer = b""
    silence_frames = 0
    speech_frames = 0

    # speech_synthesizer = GoogleSpeechSynthesizer()
    settings = YandexSettings()
    logger.info("Settings: %s", settings)
    speech_synthesizer = YandexSpeechSynthesizer(YandexCredentialsProvider(settings))
    response_queue = asyncio.Queue()

    try:
        async with CallManager(ip, port) as call_manager:
            response_queue_worker_task = asyncio.create_task(
                _response_queue_worker(response_queue, call_manager, speech_synthesizer)
            )
            async for ulaw_data, addr in call_manager.audio_channel(packet_size=2048):
                # Append the received ulaw data to the buffer
                buffer += ulaw_data

                # Count the number of frames of silence and speech
                if is_silence(ulaw_data, SILENCE_RMS_THRESHOLD):
                    silence_frames += 1
                    speech_frames = 0
                else:
                    speech_frames += 1
                    silence_frames = 0

                # If we have enough speech frames, stop the current playback
                if speech_frames == SPEECH_FRAMES_THRESHOLD:
                    logger.info("Speech detected, stopping playback.")
                    # await response_queue.clear()
                    async with lock:
                        await _empty_queue(response_queue)
                        if call_manager.is_playing():
                            call_manager.cancel_play()

                # If we have enough silence frames, process the buffer
                if silence_frames >= SILENCE_FRAMES_THRESHOLD:
                    # Trim the buffer to remove the silence frames
                    buffer = buffer[: -silence_frames * 160]

                    # If the buffer is empty, reset it and continue
                    if len(buffer) == 0:
                        buffer = b""
                        silence_frames = 0
                        speech_frames = 0
                        continue

                    logger.info(
                        f"Silence detected. Buffer size: {len(buffer)}, {len(buffer) / (SAMPLE_RATE * CHANNELS)} seconds"
                    )

                    # Recognize text from the buffer
                    # TODO: make async
                    text = speech_recognizer.recognize(buffer)
                    logger.info("Recognized text: %s", text)

                    if text:
                        # Send the recognized text to the LLM service
                        logger.info("Отправляем в LLM текст: %s", text)
                        response_text = await llm_service.generate_async(text)
                        logger.info("Ответ от LLM: %s", response_text)

                        # Split the response text into manageable chunks
                        chunks = split_text(response_text)
                        logger.info("Разделенный ответ на части: %s", chunks)

                        for chunk in chunks:
                            await response_queue.put(ResponseChunk(chunk, addr))

                    buffer = b""
                    silence_frames = 0
                    speech_frames = 0
    except KeyboardInterrupt:
        pass
    finally:
        response_queue_worker_task.cancel()


if __name__ == "__main__":
    asyncio.run(start("0.0.0.0", 10000))
