import asyncio
import audioop
import logging
import re

import numpy as np
from call_manager import CallManager
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
SPEECH_FRAMES_THRESHOLD = 10  # Количество кадров речи для распозравания активной речи
SILENCE_RMS_THRESHOLD = 30  # RMS амплитуда для определения тишины


TEST_TEXT = """
два.
- Да, господин! – воскликнул он радостно и с энтузиазмом. – Это так здорово! И вы очень хорошо это делаете! Я просто в восторге от вашей работы!
Ребенок кивнул головой:
– Спасибо вам большое за вашу работу, госпожа. А теперь позвольте мне присесть на диван.
Она села рядом со мной и принялась убирать волосы у меня из головы. Я взял ее руки под мышку и поцеловал их, словно они были моей собственностью. Она прижалась
"""


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
            r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!|\n)\s", text
        )
        if sentence.strip()
    ]


async def generate_speech_and_play(
    text: str, call_manager: CallManager, speech_generator: SpeechGenerator, addr: tuple[str, int], response_prefilled: bool
):
    # Generate u-law response for the text
    logger.info("Generating u-law response for text: %s", text)
    ulaw_response = await speech_generator.generate_speech_async(text)

    # For the first time we need to send silence before the response
    if not response_prefilled:
        ulaw_response = (
            b"\xff" * 160 * 40 + ulaw_response
        )

    # Play the generated response
    await call_manager.play_next(ulaw_response, addr, frame_duration_ms=20)
    # await asyncio.sleep(0)


async def _empty_queue(queue: asyncio.Queue):
    """Empties the given asyncio queue by consuming all items without processing them."""
    while not queue.empty():
        await queue.get()
        queue.task_done()
    logger.info("Queue emptied.")


async def start(ip: str, port: int, llm_service: LLMService):
    logger.info("Starting RTP recognizer on %s:%s", ip, port)

    buffer = b""
    silence_frames = 0
    speech_frames = 0
    response_prefilled = False

    speech_recognizer = SpeechRecognizer()
    speech_generator = SpeechGenerator()
    response_queue = asyncio.Queue()

    async with CallManager(ip, port) as call_manager:
        async for ulaw_data, addr in call_manager.audio_channel(packet_size=2048):
            # if not response_queue.empty():
            if not call_manager.is_playing() and not response_queue.empty():
                # If there are responses in the queue, play them
                chunk = await response_queue.get()
                logger.info("Playing response chunk: %s", chunk)
                await generate_speech_and_play(
                    chunk, call_manager, speech_generator, addr, response_prefilled
                )
                response_prefilled = True
                response_queue.task_done()
                # await asyncio.sleep(0.3)
                # continue

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
            if speech_frames >= SPEECH_FRAMES_THRESHOLD and call_manager.is_playing():
                logger.info("Speech detected, stopping playback.")
                call_manager.cancel_play()
                await _empty_queue(response_queue)

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
                text = speech_recognizer.recognize(buffer)
                logger.info("Recognized text: %s", text)

                if text:
                    # Send the recognized text to the LLM service
                    logger.info("Отправляем в LLM текст: %s", text)
                    response_text = TEST_TEXT
                    response_text = await llm_service.generate_async(text)
                    logger.info("Ответ от LLM: %s", response_text)

                    # Split the response text into manageable chunks
                    chunks = split_text(response_text)
                    logger.info("Разделенный ответ на части: %s", chunks)

                    for chunk in chunks:
                        # logger.info("Playing response chunk: %s", chunk)
                        # await generate_speech_and_play(
                        #     chunk, call_manager, speech_generator, addr, response_prefilled
                        # )
                        # response_prefilled = True
                        response_queue.put_nowait(chunk)

                    # for chunk in chunks:
                    #     # Generate u-law response for the current chunk
                    #     logger.info("Generating u-law response for chunk: %s", chunk)
                    #     current_ulaw_response = await speech_generator.generate_speech(
                    #         chunk
                    #     )

                    #     # For the first time we need to send silence before the response
                    #     if not response_prefilled:
                    #         current_ulaw_response = (
                    #             b"\xff" * 160 * 40 + current_ulaw_response
                    #         )
                    #         response_prefilled = True

                    #     # Play the generated response
                    #     await call_manager.play_next(current_ulaw_response, addr)
                    #     await asyncio.sleep(0)
                    
                buffer = b""
                silence_frames = 0
                speech_frames = 0

    # rtp_manager = RTPManager(ip, port)
    # # TODO
    # try:
    #     recognizer = SpeechRecognizer()
    #     speech_generator = SpeechGenerator()
    #     logger.info(f"Listening for RTP on {ip}:{port}...")
    #     async for ulaw_data, addr in rtp_manager.audio_channel(packet_size=2048):
    #         buffer += ulaw_data

    #         if is_silence(ulaw_data, SILENCE_RMS_THRESHOLD):
    #             silence_frames += 1
    #             speech_frames = 0
    #         else:
    #             speech_frames += 1
    #             silence_frames = 0

    #         if speech_frames >= SPEECH_FRAMES_THRESHOLD and rtp_manager.is_playing():
    #             logger.info("Speech detected, stopping playback.")
    #             rtp_manager.cancel_play()

    #         if silence_frames >= SILENCE_FRAMES_THRESHOLD:
    #             buffer = buffer[: -silence_frames * 160]
    #             if len(buffer) == 0:
    #                 buffer = b""
    #                 silence_frames = 0
    #                 continue

    #             logger.info(
    #                 f"Silence detected. Buffer size: {len(buffer)}, {len(buffer) / (SAMPLE_RATE * CHANNELS)} seconds"
    #             )

    #             # Распознаем текст из буфера
    #             text = recognizer.recognize(buffer)
    #             logger.info("Recognized text: %s", text)

    #             if text:
    #                 logger.info("Отправляем в LLM текст: %s", text)
    #                 response_text = llm_service.generate(text)
    #                 logger.info("Ответ от LLM: %s", response_text)

    #                 chunks = split_text(response_text)
    #                 logger.info("Разделенный ответ на части: %s", chunks)

    #                 # response_text = text
    #                 # TODO генерировать по частям, если текст длинный, use queue
    #                 logger.info("Generating u-law response for Asterisk")
    #                 current_ulaw_response = speech_generator.generate_speech(
    #                     response_text
    #                 )

    #                 # For the first time we need to send silence before the response
    #                 # TODO вынести в метод
    #                 if not response_prefilled:
    #                     current_ulaw_response = (
    #                         b"\xff" * 160 * 40 + current_ulaw_response
    #                     )
    #                     response_prefilled = True

    #                 await rtp_manager.play(current_ulaw_response, addr)

    #             buffer = b""
    #             silence_frames = 0

    # except KeyboardInterrupt:
    #     logger.info("Stopped by user.")
    # finally:
    #     rtp_manager.close()


if __name__ == "__main__":
    asyncio.run(start("0.0.0.0", 10000))
