import audioop
import os
import socket
import logging
import json
import time
import random
import io

from gtts import gTTS
import numpy as np
from vosk import Model, KaldiRecognizer
from pydub import AudioSegment

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Параметры для прослушивания RTP
LISTEN_IP = '0.0.0.0'
LISTEN_PORT = 10000

# Параметры для RTP
SAMPLE_RATE = 8000 # Частота дискретизации входящего аудио
CHANNELS = 1 # Количество каналов

# Параметры для обработки аудио
OUTPUT_FILE = 'output.raw'  # Имя файла для записи
SILENCE_FRAMES_THRESHOLD = 20  # Количество кадров тишины для завершения фразы
SILENCE_RMS_THRESHOLD = 30  # RMS амплитуда для определения тишины

# Создаем UDP-сокет
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LISTEN_IP, LISTEN_PORT))

sock_response = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

buffer = b''

# Инициализация модели Vosk
model_path = "vosk-model-small-ru-0.22"
# model_path = "vosk-model-ru-0.42"
if not os.path.exists(model_path):
    logger.error("Модель Vosk не найдена. Скачайте с https://alphacephei.com/vosk/models и распакуйте.")
    exit(1)

model = Model(model_path)
recognizer = KaldiRecognizer(model, 16000)
silence_frames = 0

logger.info(f"Listening for RTP on {LISTEN_IP}:{LISTEN_PORT}...")


def is_silence(samples, threshold_rms=100):
    """Определяет, является ли аудио блок тишиной на основе RMS"""
    pcm_audio_8k = audioop.ulaw2lin(samples, 2)
    amplitudes = np.frombuffer(pcm_audio_8k, dtype=np.int16).astype(np.float32)
    rms = np.sqrt(np.mean(amplitudes ** 2))
    # Uncomment this line to log RMS values
    # logger.info("RMS amplitude: %.2f, len: %s", rms, len(samples))
    return rms < threshold_rms


def stream_ulaw_rtp(file_path: str, target_ip: str, target_port: int, frame_duration_ms=20):
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

    with open(file_path, 'rb') as f:
        while True:
            payload = f.read(160)  # 20ms @ 8kHz = 160 bytes
            if not payload:
                break

            # Обновляем заголовки
            rtp_header[2:4] = sequence_number.to_bytes(2, 'big')
            rtp_header[4:8] = timestamp.to_bytes(4, 'big')

            packet = rtp_header + payload
            sock_response.sendto(packet, (target_ip, target_port))

            sequence_number += 1
            timestamp += 160  # для G.711: 8kHz → 160 samples per 20ms

            time.sleep(frame_duration_ms / 1000)


def text_to_ulaw_stream(text: str) -> bytes:
    # Генерируем речь в mp3 с помощью gTTS
    tts = gTTS(text, lang='ru')
    mp3_fp = io.BytesIO()
    tts.write_to_fp(mp3_fp)
    mp3_fp.seek(0)

    # Загружаем mp3 в pydub
    audio = AudioSegment.from_file(mp3_fp, format="mp3")

    # Преобразуем в u-law: 8kHz, 1 канал, 8 бит
    ulaw_audio = audio.set_frame_rate(8000).set_channels(1).set_sample_width(1)

    # Экспорт в поток в формате WAV (с u-law кодеком)
    raw_fp = io.BytesIO()
    ulaw_audio.export(raw_fp, format="raw", codec="pcm_mulaw")
    return raw_fp.getvalue()


def stream_ulaw_rtp_from_bytes(ulaw_data: bytes, target_ip: str, target_port: int, frame_duration_ms=20):
    # RTP header setup
    ssrc = random.randint(0, 0xFFFFFFFF)
    sequence_number = 0
    timestamp = 0

    # 20ms @ 8kHz = 160 samples per frame for G.711
    frame_size = int(8000 * frame_duration_ms / 1000)  # 160 for 20ms

    for i in range(0, len(ulaw_data), frame_size):
        payload = ulaw_data[i:i + frame_size]
        if len(payload) < frame_size:
            break  # Обрезанный последний пакет можно пропустить или дополнить нулями

        # Формируем RTP-заголовок
        rtp_header = bytearray(12)
        rtp_header[0] = 0x80                        # Версия: 2
        rtp_header[1] = 0x00                        # Payload Type: 0 (G.711 μ-law)
        rtp_header[2:4] = sequence_number.to_bytes(2, 'big')
        rtp_header[4:8] = timestamp.to_bytes(4, 'big')
        rtp_header[8:12] = ssrc.to_bytes(4, 'big')

        packet = rtp_header + payload
        sock.sendto(packet, (target_ip, target_port))

        sequence_number = (sequence_number + 1) % 65536
        timestamp += frame_size

        time.sleep(frame_duration_ms / 1000)


try:
    with open(OUTPUT_FILE, 'wb') as f:
        while True:
            data, addr = sock.recvfrom(2048)  # получаем RTP-пакет
            ulaw_data = data[12:]  # Пропускаем RTP заголовок (обычно 12 байт)
            f.write(ulaw_data)

            buffer += ulaw_data

            silence_frames = silence_frames + 1 if is_silence(ulaw_data, SILENCE_RMS_THRESHOLD) else 0

            if silence_frames >= SILENCE_FRAMES_THRESHOLD:
                buffer = buffer[:-silence_frames*160] # Убираем тишину из буфера
                if len(buffer) == 0:
                    buffer = b''
                    silence_frames = 0
                    continue

                logger.info(f"Silence detected. Buffer size: {len(buffer)}, {len(buffer) / (SAMPLE_RATE * CHANNELS)} seconds")

                pcm_audio_8k = audioop.ulaw2lin(buffer, 2)
                pcm_audio_16k, _ = audioop.ratecv(pcm_audio_8k, 2, 1, 8000, 16000, None)

                # Подадим аудио
                if recognizer.AcceptWaveform(pcm_audio_16k):
                    result = recognizer.Result()
                else:
                    result = recognizer.FinalResult()

                # Получаем распознанный текст
                text = json.loads(result).get("text", "")
                logger.info(f"Распознанный текст: {text}")
                buffer = b''
                silence_frames = 0

                # TODO: Отправить голосовой ответ обратно в Asterisk
                logger.info("Отправляем ответ в Asterisk на %s:%s", addr[0], addr[1])
                time.sleep(0.5)  # Задержка для синхронизации
                stream_ulaw_rtp("response.ulaw", addr[0], addr[1])

except KeyboardInterrupt:
    logger.info("Stopped by user.")
finally:
    sock.close()
    sock_response.close()
