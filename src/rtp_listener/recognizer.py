import audioop
import os
import socket
import logging
import json

import numpy as np
from vosk import Model, KaldiRecognizer

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

except KeyboardInterrupt:
    logger.info("Stopped by user.")
finally:
    sock.close()
