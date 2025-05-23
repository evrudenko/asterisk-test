import asyncio
import websockets
import base64
import json
import logging
from typing import Any

from src.ari_handler.connector import OutputAudioPacket, InputAudioPacket

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def decode_packet(packet: Any) -> OutputAudioPacket:
    try:
        json_data = json.loads(packet)
        decoded_data = base64.b64decode(json_data.get("audio_data"))
        return OutputAudioPacket(
            audio_data=decoded_data,
            sender_ip=json_data.get("sender_ip"),
            sender_port=json_data.get("sender_port")
        )
    except Exception as e:
        logger.error("Decoding error: %s", e)
        raise e


def encode_packet(packet: InputAudioPacket) -> str:
    try:
        json_data = {
            "audio_data": base64.b64encode(packet.audio_data).decode('utf-8'),
            "reciever_ip": packet.reciever_ip,
            "reciever_port": packet.reciever_port
        }
        return json.dumps(json_data)
    except Exception as e:
        logger.error("Encoding error: %s", e)
        raise e


async def receive_messages(websocket):
    try:
        count = 0
        async for message in websocket:
            packet = decode_packet(message)
            count += 1
            if count % 500 == 0:
                logger.info("Received %d packets", count)
                await send_message(
                    websocket,
                    packet.sender_ip,
                    packet.sender_port
                )
    except websockets.ConnectionClosed:
        print("🔌 Соединение закрыто сервером.")


async def send_message(websocket, reciever_ip, reciever_port):
    try:
        ulaw_data = b""
        with open("src/rtp_listener/response.ulaw", "rb") as f:
            ulaw_data = f.read()

        if ulaw_data:
            logger.info("Отправка ulaw данных размером %s:", len(ulaw_data))
            packet = InputAudioPacket(
                audio_data=ulaw_data,
                reciever_ip=reciever_ip,
                reciever_port=reciever_port,
            )
            await websocket.send(encode_packet(packet))
    except websockets.ConnectionClosed:
        print("🔌 Невозможно отправить: соединение закрыто.")

async def main():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        print("🔗 Подключено к серверу. Ожидаем сообщения...")
        await receive_messages(websocket)

if __name__ == "__main__":
    asyncio.run(main())
