import socket
import threading
import datetime
import logging


# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def handle_client(conn, addr):
    logger.info(f"[+] Connected from {addr}")
    buffer = b''
    audio_file = f"recording_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.ulaw"

    try:
        conn_file = conn.makefile('rb')
        # Чтение и печать команд
        while True:
            line = conn_file.readline()
            if not line:
                break
            line = line.decode('utf-8').strip()
            logger.info(f"[FS] {line}")

            if line == '':
                # End of headers
                break

        # Сообщаем FreeSWITCH, что мы готовы принимать media
        conn.send(b'connect\n\n')

        # Чтение RTP-потока
        with open(audio_file, 'wb') as f:
            while True:
                data = conn.recv(1024)
                logger.info(f"[RTP] Received {len(data)} bytes")
                if not data:
                    break
                buffer += data
                f.write(data)

    except Exception as e:
        logger.info(f"[!] Error: {e}")
    finally:
        logger.info(f"[-] Disconnected from {addr}")
        conn.close()
        logger.info(f"[✔] Audio saved to: {audio_file}")


def start_socket_server(host='0.0.0.0', port=10000):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(5)
    logger.info(f"[✓] Listening for FreeSWITCH on {host}:{port}...")

    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        server.close()


if __name__ == "__main__":
    start_socket_server()
