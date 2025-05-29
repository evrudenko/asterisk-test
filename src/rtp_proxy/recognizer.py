import asyncio
import audioop
import os
import socket
import logging
import json
import random
import io

from gtts import gTTS
import numpy as np
from vosk import Model, KaldiRecognizer
from pydub import AudioSegment

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Параметры для RTP
SAMPLE_RATE = 8000 # Частота дискретизации входящего аудио
CHANNELS = 1 # Количество каналов

# Параметры для обработки аудио
SILENCE_FRAMES_THRESHOLD = 20  # Количество кадров тишины для завершения фразы
SILENCE_RMS_THRESHOLD = 30  # RMS амплитуда для определения тишины


def get_recognizer():
    # Инициализация модели Vosk
    model_path = "vosk-model-small-ru-0.22"
    # model_path = "vosk-model-ru-0.42"
    if not os.path.exists(model_path):
        logger.error("Модель Vosk не найдена. Скачайте с https://alphacephei.com/vosk/models и распакуйте.")
        exit(1)

    model = Model(model_path)
    return KaldiRecognizer(model, 16000)


def is_silence(samples, threshold_rms=100):
    """Определяет, является ли аудио блок тишиной на основе RMS"""
    pcm_audio_8k = audioop.ulaw2lin(samples, 2)
    amplitudes = np.frombuffer(pcm_audio_8k, dtype=np.int16).astype(np.float32)
    rms = np.sqrt(np.mean(amplitudes ** 2))
    # Uncomment this line to log RMS values
    # logger.info("RMS amplitude: %.2f", rms)
    return rms < threshold_rms


async def stream_ulaw_rtp(sock, file_path: str, target_ip: str, target_port: int):
    with open(file_path, 'rb') as f:
        ulaw_data = f.read()
    return await stream_ulaw_rtp_bytes(sock, ulaw_data, target_ip, target_port)


async def stream_ulaw_rtp_bytes(sock, ulaw_data: bytes, target_ip: str, target_port: int):
    logger.info("Streaming ulaw data size %s:", len(ulaw_data))
    loop = asyncio.get_running_loop()

    frame_duration_ms = 20
    frame_size = int(SAMPLE_RATE * frame_duration_ms / 1000)  # 160 bytes per 20ms

    # Случайный SSRC
    ssrc = random.randint(0, 0xFFFFFFFF)
    rtp_header = bytearray([
        0x80, 0x00, 0x00, 0x00,      # Version, Payload Type, Sequence Number
        0x00, 0x00, 0x00, 0x00,      # Timestamp
        (ssrc >> 24) & 0xFF,
        (ssrc >> 16) & 0xFF,
        (ssrc >> 8) & 0xFF,
        ssrc & 0xFF
    ])

    sequence_number = 0
    timestamp = 0

    for i in range(0, len(ulaw_data), frame_size):
        payload = ulaw_data[i:i + frame_size]

        # Обновляем заголовки
        rtp_header[2:4] = sequence_number.to_bytes(2, 'big')
        rtp_header[4:8] = timestamp.to_bytes(4, 'big')

        packet = rtp_header + payload
        await loop.sock_sendto(sock, packet, (target_ip, target_port))

        sequence_number += 1
        timestamp += frame_size  # для G.711: 8kHz → 160 samples per 20ms

        await asyncio.sleep(frame_duration_ms / 1000)


def text_to_ulaw_stream(text: str) -> bytes:
    # Генерируем речь в mp3 с помощью gTTS
    tts = gTTS(text, lang='ru')
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

    # Экспорт в поток в формате WAV (с u-law кодеком)
    raw_fp = io.BytesIO()
    ulaw_audio.export(raw_fp, format="mulaw", codec="pcm_mulaw")
    return raw_fp.getvalue()


def recognize_ulaw_audio(recognizer, ulaw_data: bytes) -> str:
    """Распознает текст из u-law аудио"""
    pcm_audio_8k = audioop.ulaw2lin(ulaw_data, 2)
    pcm_audio_16k, _ = audioop.ratecv(pcm_audio_8k, 2, 1, 8000, 16000, None)

    if recognizer.AcceptWaveform(pcm_audio_16k):
        result = recognizer.Result()
    else:
        result = recognizer.FinalResult()

    # Получаем распознанный текст
    text = json.loads(result).get("text", "")
    return text


async def start(ip: str, port: int):
    loop = asyncio.get_running_loop()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))
    sock.setblocking(False)

    buffer = b''
    silence_frames = 0
    response_prefilled = False

    try:
        recognizer = get_recognizer()
        logger.info(f"Listening for RTP on {ip}:{port}...")
        while True:
            data, addr = await loop.sock_recvfrom(sock, 2048)  # получаем RTP-пакет
            ulaw_data = data[12:]  # Пропускаем RTP заголовок (обычно 12 байт)

            buffer += ulaw_data

            silence_frames = silence_frames + 1 if is_silence(ulaw_data, SILENCE_RMS_THRESHOLD) else 0

            if silence_frames >= SILENCE_FRAMES_THRESHOLD:
                buffer = buffer[:-silence_frames*160]
                if len(buffer) == 0:
                    buffer = b''
                    silence_frames = 0
                    continue

                logger.info(f"Silence detected. Buffer size: {len(buffer)}, {len(buffer) / (SAMPLE_RATE * CHANNELS)} seconds")

                # Распознаем текст из буфера
                text = recognize_ulaw_audio(recognizer, buffer)
                logger.info(f"Распознанный текст: {text}")

                if text:
                    logger.info("Отправляем ответ в Asterisk на %s:%s", addr[0], addr[1])
                    current_ulaw_response = text_to_ulaw_stream(text)
                    # For the first time we need to send silence before the response
                    if not response_prefilled:
                        current_ulaw_response = b'\xff' * 160 * 40 + current_ulaw_response
                        response_prefilled = True
                    asyncio.create_task(stream_ulaw_rtp_bytes(sock, current_ulaw_response, addr[0], addr[1]))

                buffer = b''
                silence_frames = 0

    except KeyboardInterrupt:
        logger.info("Stopped by user.")
    finally:
        sock.close()


if __name__ == "__main__":
    asyncio.run(start("0.0.0.0", 10000))
