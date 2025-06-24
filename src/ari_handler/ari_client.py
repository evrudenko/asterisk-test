import asyncio
import json
import logging
from typing import Optional

import aiohttp
from models.event import Event
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class AriClient:
    def __init__(
        self,
        host: str,
        port: int,
        username: str = "ariuser",
        password: str = "ariuser",
        app: str = "voicebot",
    ):
        self._base_url = f"http://{host}:{port}/ari"
        self._ws_url = f"ws://{host}:{port}/ari/events?app={app}&subscribeAll=true"
        self._username = username
        self._password = password
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws = None
        self._ws_task = None
        self._running = False
        self._event_queue = asyncio.Queue()

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self._username, self._password)
        )
        await self._open_ws_connection()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_ws_connection()
        if self._session:
            await self._session.close()

    def __aiter__(self):
        return self

    async def __anext__(self) -> Event:
        event = await self._event_queue.get()
        if event is None:
            raise StopAsyncIteration
        return event

    async def create_external_media(
        self, channel_id: str, app: str, external_host: str, format: str = "ulaw"
    ) -> None:
        params = {
            "channelId": channel_id,
            "app": app,
            "external_host": external_host,
            "format": format,
            "encapsulation": "rtp",
            "transport": "udp",
            "connection_type": "client",
            "direction": "both",
        }
        response = await self._post("channels/externalMedia", params)
        if response.status == 200:
            logger.info("✅ ExternalMedia создан")
        else:
            logger.warning("⚠️ Ошибка externalMedia: %s", await response.text())

    async def start_recording(
        self,
        bridge_id: str,
        name: str,
        format: str = "wav",
        max_duration_seconds: int = 0,
        max_silence_seconds: int = 0,
        if_exists: str = "fail",
        beep: bool = True,
    ) -> None:
        params = {
            "name": name,
            "format": format,
            "maxDurationSeconds": max_duration_seconds,
            "maxSilenceSeconds": max_silence_seconds,
            "ifExists": if_exists,
            "beep": str(beep).lower(),
        }
        response = await self._post(f"bridges/{bridge_id}/record", params)
        if response.status == 201:
            logger.info("✅ Bridge recording started")
        else:
            logger.warning("⚠️ Ошибка записи моста: %s", await response.text())

    async def play_media(self, channel_id: str, media: str) -> None:
        params = {"media": media}
        response = await self._post(f"channels/{channel_id}/play", params)
        if response.status == 201:
            logger.info("✅ Media played successfully")
        else:
            logger.warning("⚠️ Ошибка воспроизведения медиа: %s", await response.text())

    async def create_bridge(self, bridge_type: str = "mixing") -> Optional[str]:
        params = {"type": bridge_type}
        response = await self._post("bridges", params)
        if response.status == 200:
            bridge = await response.json()
            logger.info("✅ Bridge created: %s", bridge.get("id"))
            return bridge.get("id")
        else:
            logger.warning("⚠️ Ошибка создания моста: %s", await response.text())
            return None

    async def add_channel_to_bridge(self, bridge_id: str, channel_id: str) -> None:
        params = {"channel": channel_id}
        response = await self._post(f"bridges/{bridge_id}/addChannel", params)
        if response.status == 204:
            logger.info("✅ Channel added to bridge successfully")
        else:
            logger.warning(
                "⚠️ Ошибка добавления канала в мост: %s", await response.text()
            )

    async def answer_channel(self, channel_id: str) -> None:
        response = await self._post(f"channels/{channel_id}/answer", {})
        if response.status == 204:
            logger.info("✅ Channel answered successfully")
        else:
            logger.warning("⚠️ Ошибка ответа на канал: %s", await response.text())

    async def _post(self, endpoint: str, params: dict) -> aiohttp.ClientResponse:
        url = f"{self._base_url}/{endpoint}"
        logger.info("POST URL: %s | Params: %s", url, params)
        async with self._session.post(url, params=params) as response:
            text = await response.text()
            logger.debug("Response [%s]: %s", response.status, text)
            return response

    async def _ws_connection_worker(self):
        async with self._session.ws_connect(self._ws_url) as websocket:
            self._ws = websocket
            while self._running:
                try:
                    msg = await websocket.receive()

                    if msg.type == aiohttp.WSMsgType.TEXT:
                        await self._handle_message(msg.data)
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        logger.info("WebSocket closed by server.")
                        break
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"WebSocket error: {msg}")
                        break

                except Exception as e:
                    logger.error(f"Error in WebSocket connection: {e}")
                    break

    async def _handle_message(self, message: str):
        try:
            event = Event.model_validate_json(message)
        except json.JSONDecodeError:
            logger.error("Failed to decode JSON message: %s", message)
        except ValidationError as e:
            logger.error(f"Validation error for event: {e}")
        else:
            await self._event_queue.put(event)

    async def _open_ws_connection(self):
        self._running = True
        self._ws_task = asyncio.create_task(self._ws_connection_worker())
        logger.info("WebSocket connection established.")

    async def _close_ws_connection(self):
        self._running = False
        if self._ws:
            await self._ws.close()
        if self._ws_task:
            await self._ws_task
        logger.info("WebSocket connection closed.")
