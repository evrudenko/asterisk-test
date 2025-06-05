import logging
import socket

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Настройки
LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 10000
OUTPUT_FILE = "output.raw"  # Имя файла для записи

# Создаем UDP-сокет
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LISTEN_IP, LISTEN_PORT))

logger.info(f"Listening for RTP on {LISTEN_IP}:{LISTEN_PORT}...")

try:
    with open(OUTPUT_FILE, "wb") as f:
        while True:
            data, addr = sock.recvfrom(2048)  # получаем RTP-пакет
            logger.info(f"Received {len(data)} bytes from {addr}")
            f.write(data[12:])
except KeyboardInterrupt:
    logger.info("Stopped by user.")
finally:
    sock.close()
