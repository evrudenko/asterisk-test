import asyncio
import socket
import logging
from dataclasses import dataclass
import json
import base64
from typing import Any
import random

import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

RTP_HOST = "0.0.0.0"
RTP_PORT = 10000

# Параметры для RTP
SAMPLE_RATE = 8000 # Частота дискретизации входящего аудио
CHANNELS = 1 # Количество каналов


@dataclass
class OutputAudioPacket:

    audio_data: bytes
    sender_ip: str
    sender_port: int


@dataclass
class InputAudioPacket:

    audio_data: bytes
    reciever_ip: str
    reciever_port: int


def decode_packet(packet: Any) -> InputAudioPacket:
    try:
        json_data = json.loads(packet)
        decoded_data = base64.b64decode(json_data.get("audio_data"))
        return InputAudioPacket(
            audio_data=decoded_data,
            reciever_ip=json_data.get("reciever_ip"),
            reciever_port=json_data.get("reciever_port")
        )
    except Exception as e:
        logger.error("Decoding error: %s", e)
        raise e


def encode_packet(packet: OutputAudioPacket) -> str:
    try:
        json_data = {
            "audio_data": base64.b64encode(packet.audio_data).decode('utf-8'),
            "sender_ip": packet.sender_ip,
            "sender_port": packet.sender_port
        }
        return json.dumps(json_data)
    except Exception as e:
        logger.error("Encoding error: %s", e)
        raise e


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
        timestamp += frame_size

        await asyncio.sleep(frame_duration_ms / 1000)


async def handle_connection(websocket):
    logger.info("Клиент WebSocket подключился")

    loop = asyncio.get_running_loop()
    rtp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rtp_sock.bind((RTP_HOST, RTP_PORT))
    rtp_sock.setblocking(False)

    async def ws_to_rtp():
        try:
            async for message in websocket:
                packet = decode_packet(message)
                await stream_ulaw_rtp_bytes(rtp_sock, packet.audio_data, packet.reciever_ip, packet.reciever_port)
        except (ConnectionClosedOK, ConnectionClosedError):
            pass

    async def rtp_to_ws():
        try:
            while True:
                data, addr = await loop.sock_recvfrom(rtp_sock, 2048)
                if not data:
                    break

                ulaw_data = data[12:]
                packet = OutputAudioPacket(
                    audio_data=ulaw_data,
                    sender_ip=addr[0],
                    sender_port=addr[1]
                )
                await websocket.send(encode_packet(packet))
        except (ConnectionClosedOK, ConnectionClosedError):
            pass

    # Запуск двух параллельных задач
    task1 = asyncio.create_task(ws_to_rtp())
    task2 = asyncio.create_task(rtp_to_ws())

    _, pending = await asyncio.wait(
        [task1, task2],
        return_when=asyncio.FIRST_COMPLETED
    )

    # Завершаем обе задачи и закрываем сокет
    for task in pending:
        task.cancel()
    rtp_sock.close()
    logger.info("Соединение закрыто")


async def run_websocket_connector(ws_host: str, ws_port: int):
    async with websockets.serve(handle_connection, ws_host, ws_port):
        logger.info(f"WebSocket сервер запущен на ws://{ws_host}:{ws_port}")
        await asyncio.Future()  # Работает бесконечно


if __name__ == "__main__":
    asyncio.run(run_websocket_connector())
