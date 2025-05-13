import audioop
import os
import socket
import logging
import json

from vosk import Model, KaldiRecognizer

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Настройки
LISTEN_IP = '0.0.0.0'
LISTEN_PORT = 10000
SAMPLE_RATE = 16000

# Создаем UDP-сокет
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LISTEN_IP, LISTEN_PORT))

buffer = b''

# Инициализация модели Vosk
model_path = "vosk-model-small-ru-0.22"
if not os.path.exists(model_path):
    logger.error("Модель Vosk не найдена. Скачайте с https://alphacephei.com/vosk/models и распакуйте.")
    exit(1)

model = Model(model_path)
recognizer = KaldiRecognizer(model, SAMPLE_RATE)

logger.info(f"Listening for RTP on {LISTEN_IP}:{LISTEN_PORT}...")

try:
    while True:
        data, addr = sock.recvfrom(2048)  # получаем RTP-пакет
        # logger.info(f"Received {len(data)} bytes from {addr}")
        # Если нужно — записывайте или обрабатывайте аудио здесь
        ulaw_data = data[12:]  # Пропускаем RTP заголовок (обычно 12 байт)
        buffer += ulaw_data
        if len(buffer) >= 8000 * 1 * 5:
            logger.info(f"Buffer size: {len(buffer)} bytes")
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

except KeyboardInterrupt:
    logger.info("Stopped by user.")
finally:
    sock.close()
