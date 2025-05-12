import asyncio
from uuid import uuid4
import time
import logging

import asyncari

from ari_client import AriClient

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

AST_HOST = "asterisk"
AST_PORT = 8088
AST_URL = f"http://{AST_HOST}:{AST_PORT}/"
AST_APP = "voicebot"
AST_USER = "ariuser"
AST_PASS = "ariuser"


async def on_start(client):
    logger.info("🎧 Слушаем вызовы")
    async with client.on_channel_event('StasisStart') as listener:
        async for objs, event in listener:
            channel = objs['channel']
            if not channel.caller['number']:
                logger.info(f"❌ Пропускаем вызов без номера")
                continue
            logger.info(f"📞 Входящий звонок от {channel.caller['number']}")

            await channel.answer()

            new_channel_id = uuid4()
            await create_external_media(new_channel_id)
            bridge = await client.bridges.create(type='mixing')

            await bridge.addChannel(channel=channel.id)
            await bridge.addChannel(channel=new_channel_id)

            logger.info("🎧 Подключён к внешнему потоку, запускай TTS стример")


async def create_external_media(channel_id):
    ari_client = AriClient(AST_HOST, AST_PORT)
    ari_client.channels_external_media(
        channel_id=channel_id,
        app=AST_APP,
        external_host='rtp_listener:10000',
        format='slin16',
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
