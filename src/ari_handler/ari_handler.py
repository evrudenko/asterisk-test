import asyncio
from uuid import uuid4
import time
import logging
import os

import asyncari

from ari_client import AriClient
from connector import run_websocket_connector
# from recognizer import start as start_recognizer

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AST_HOST = os.getenv("AST_HOST", "asterisk")
AST_PORT = os.getenv("AST_PORT",  8088)
AST_URL = os.getenv("AST_URL",  f"http://{AST_HOST}:{AST_PORT}/")
AST_APP = os.getenv("AST_APP", "voicebot")
AST_USER = os.getenv("AST_USER", "ariuser")
AST_PASS = os.getenv("AST_PASS", "ariuser")


running_rtp_listeners = {}


async def handle_stasis_start(client):
    async with client.on_channel_event("StasisStart") as listener:
        async for objs, event in listener:
            channel = objs["channel"]
            if not channel.caller["number"]:
                logger.info("❌ Пропускаем вызов без номера")
                continue
            logger.info(f"📞 Входящий звонок от {channel.caller['number']}")
            await channel.answer()
            new_channel_id = uuid4()

            logger.info("Creating external media")
            await create_external_media(new_channel_id, external_host="ari_handler:10000")
            bridge = await client.bridges.create(type="mixing")
            await bridge.addChannel(channel=channel.id)
            await bridge.addChannel(channel=new_channel_id)
            logger.info("External media created")

            # task = asyncio.create_task(start_recognizer("0.0.0.0", 10000))
            task = asyncio.create_task(run_websocket_connector("0.0.0.0", 8765))

            running_rtp_listeners[channel.id] = task


async def handle_stasis_end(client):
    async with client.on_channel_event("StasisEnd") as listener:
        async for channel, event in listener:
            logger.info(f"🚫 Завершён вызов для канала {channel.id}")
            # Здесь можно добавить дополнительную логику по завершению вызова
            if channel.id in running_rtp_listeners:
                task = running_rtp_listeners[channel.id]
                task.cancel()
                del running_rtp_listeners[channel.id]
                logger.info(f"🛑 Остановлен RTP listener для канала {channel.id}")


async def on_start(client):
    logger.info("🎧 Слушаем вызовы")
    await asyncio.gather(handle_stasis_start(client), handle_stasis_end(client))


async def create_external_media(channel_id, external_host):
    ari_client = AriClient(AST_HOST, AST_PORT)
    ari_client.channels_external_media(
        channel_id=channel_id,
        app=AST_APP,
        external_host=external_host,
        format="ulaw",
    )


async def start():
    async with asyncari.connect(AST_URL, AST_APP, AST_USER, AST_PASS) as client:
        logger.info("🔌 Подключение к Asterisk установлено")
        client.taskgroup.start_soon(on_start, client)
        # Run the WebSocket
        async for m in client:
            logger.info("** EVENT ** %s", m)


if __name__ == "__main__":
    logger.info("Fall asleep for 2 seconds...")
    time.sleep(2)
    logger.info("Awake")
    asyncio.run(start())
