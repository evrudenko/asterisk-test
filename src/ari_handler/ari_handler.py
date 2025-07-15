import asyncio
import logging
import os
from uuid import uuid4

from ari_client import AriClient
from kaldi_speech_recognizer import KaldiSpeechRecognizer
from llm_service import LLMService
from main import start as start_recognizer
from models.channel_state import ChannelState
from models.event import Event
from models.event_type import EventType
from yandex_credentials_provider import YandexCredentialsProvider
from yandex_settings import YandexSettings
from yandex_speech_recognizer import YandexSpeechRecognizer
from yandex_speech_synthesizer import YandexSpeechSynthesizer

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

AST_HOST = os.getenv("AST_HOST", "asterisk")
AST_PORT = os.getenv("AST_PORT", 8088)
AST_URL = os.getenv("AST_URL", f"http://{AST_HOST}:{AST_PORT}/")
AST_APP = os.getenv("AST_APP", "voicebot")
AST_USER = os.getenv("AST_USER", "ariuser")
AST_PASS = os.getenv("AST_PASS", "ariuser")

yandex_credentials_provider = YandexCredentialsProvider(YandexSettings())

logger.info("Creating SpeechRecognizer instance")
speech_recognizer = KaldiSpeechRecognizer(model_path="vosk-model-ru-0.42")
# speech_recognizer = YandexSpeechRecognizer(yandex_credentials_provider)
logger.info("SpeechRecognizer instance created")

logger.info("Creating SpeechSynthesizer instance")
speech_synthesizer = YandexSpeechSynthesizer(yandex_credentials_provider)
logger.info("SpeechSynthesizer instance created")

logger.info("Creating LLMService instance")
llm_service = LLMService()
logger.info("LLMService instance created")

running_rtp_listeners = {}


async def create_external_media(client: AriClient, channel_id: str) -> str:
    logger.info("Creating external media")
    external_channel_id = uuid4()
    await client.create_external_media(
        channel_id=external_channel_id,
        app=AST_APP,
        external_host="ari-handler:10000",
        format="ulaw",
    )
    bridge_id = await client.create_bridge(bridge_type="mixing")
    logger.info("Created bridge: %s", bridge_id)
    await client.add_channel_to_bridge(bridge_id=bridge_id, channel_id=channel_id)
    await client.add_channel_to_bridge(
        bridge_id=bridge_id, channel_id=external_channel_id
    )

    return bridge_id


async def handle_stasis_start(client: AriClient, event: Event):
    channel = event.channel

    if channel.state != ChannelState.RING:
        logger.info("Channel not ring, skipping...")
        return

    logger.info(f"📞 Входящий звонок от {channel.caller.number}")

    await client.answer_channel(channel.id)

    await client.play_media(channel.id, "sound:hello-world")

    bridge_id = await create_external_media(client, channel.id)

    await client.start_recording(
        bridge_id=bridge_id,
        format="wav",
        name=f"recording_{channel.id}",
    )

    task = asyncio.create_task(
        start_recognizer(
            "0.0.0.0", 10000, llm_service, speech_recognizer, speech_synthesizer
        )
    )

    running_rtp_listeners[channel.id] = task


async def handle_stasis_end(client: AriClient, event: Event):
    logger.info(f"🚫 Завершён вызов для канала {event.channel.id}")
    if event.channel.id in running_rtp_listeners:
        task = running_rtp_listeners[event.channel.id]
        task.cancel()
        del running_rtp_listeners[event.channel.id]
        logger.info(f"🛑 Остановлен RTP listener для канала {event.channel.id}")


async def process_event(client: AriClient, event: Event):
    if event.type != EventType.UNKNOWN:
        logger.info(f"Received event: {event}")
    if event.type == EventType.STASIS_START:
        await handle_stasis_start(client, event)
    elif event.type == EventType.STASIS_END:
        await handle_stasis_end(client, event)


async def start():
    async with AriClient(AST_HOST, AST_PORT, AST_USER, AST_PASS, AST_APP) as client:
        async for event in client:
            await process_event(client, event)


if __name__ == "__main__":
    asyncio.run(start())
