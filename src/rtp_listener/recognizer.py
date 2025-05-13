import socket
import logging
import numpy as np
from vosk import Model, KaldiRecognizer
import json
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Настройки
LISTEN_IP = '0.0.0.0'
LISTEN_PORT = 10000
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 500  # амплитуда для определения тишины
SILENCE_DURATION = 1.0  # секунды тишины для завершения фразы

# Инициализация модели Vosk
model_path = "vosk-model-small-ru-0.22"
if not os.path.exists(model_path):
    logger.error("Модель Vosk не найдена. Скачайте с https://alphacephei.com/vosk/models и распакуйте.")
    exit(1)

model = Model(model_path)
recognizer = KaldiRecognizer(model, SAMPLE_RATE)

# Создаем UDP-сокет
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LISTEN_IP, LISTEN_PORT))

logger.info(f"Listening for RTP on {LISTEN_IP}:{LISTEN_PORT}...")

buffer = b''
silence_start = None

def is_silence(samples, threshold):
    """Определяет, является ли аудио блок тишиной"""
    amplitudes = np.abs(np.frombuffer(samples, dtype=np.int16))
    return np.max(amplitudes) < threshold

try:
    while True:
        data, addr = sock.recvfrom(2048)

        # RTP header usually 12 bytes — skip it if needed
        rtp_payload = data[12:]

        buffer += rtp_payload

        if len(buffer) >= SAMPLE_RATE * 2 * 0.5:  # каждые 0.5 секунды (16k * 2 байта)
            if is_silence(buffer, SILENCE_THRESHOLD):
                if silence_start is None:
                    silence_start = True
                else:
                    # Пауза продолжается — обрабатываем накопленную фразу
                    if recognizer.AcceptWaveform(buffer):
                        result = json.loads(recognizer.Result())
                        if result.get("text"):
                            logger.info(f"[RECOGNIZED]: {result['text']}")
                    else:
                        partial = json.loads(recognizer.PartialResult())
                        if partial.get("partial"):
                            logger.info(f"[PARTIAL]: {partial['partial']}")
                    buffer = b''
            else:
                silence_start = None
                recognizer.AcceptWaveform(buffer)
                buffer = b''

except KeyboardInterrupt:
    logger.info("Stopped by user.")
finally:
    sock.close()
