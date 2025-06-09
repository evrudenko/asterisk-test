import logging

import requests

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AriClient:
    """ARI Client."""

    def __init__(
        self, host: str, port: int, username: str = "ariuser", password: str = "ariuser"
    ):
        """
        Args:
            host (str): Hostname of the Asterisk server.
            port (int): Port of the Asterisk ARI interface.
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    async def channels_external_media(
        self, channel_id: str, app: str, external_host: str, format: str = "ulaw"
    ):
        """
        Create an external media channel.
        Args:
            channel_id (str): The ID of the channel.
            app (str): The application name.
            external_host (str): Hostname/IP:port of external host.
            format (str): Format to encode audio in. Default is 'ulaw'.
        """
        url = f"http://{self.host}:{self.port}/ari/channels/externalMedia"
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
        logger.info("URL: %s", url)
        response = requests.post(
            url, params=params, auth=(self.username, self.password)
        )
        if response.status_code == 200:
            logger.info("✅ ExternalMedia создан: %s", response.json())
        else:
            logger.warning(
                "⚠️ Ошибка externalMedia: %s - %s", response.status_code, response.text
            )

    async def bridge_start_recording(
        self,
        bridge_id: str,
        name: str,
        format: str = "wav",
        max_duration_seconds: int = 0,
        max_silence_seconds: int = 0,
        if_exists: str = "fail",
        beep: bool = True,
    ) -> None:
        """
        Start recording a bridge.

        :param bridge_id: The ID of the bridge to record.
        :param name: The name of the recording file.
        :param format: The format of the recording (default is 'wav').
        :param max_duration_seconds: Maximum duration of the recording in seconds (default is 0, meaning no limit).
        :param max_silence_seconds: Maximum silence duration in seconds before stopping the recording (default is 0, meaning no limit).
        :param if_exists: What to do if the recording file already exists (default is 'fail').
        :param beep: Whether to play a beep sound before starting the recording (default is True).
        """
        url = f"http://{self.host}:{self.port}/ari/bridges/{bridge_id}/record"
        params = {
            "name": name,
            "format": format,
            "maxDurationSeconds": max_duration_seconds,
            "maxSilenceSeconds": max_silence_seconds,
            "ifExists": if_exists,
            "beep": beep,
        }
        logger.info("URL: %s", url)
        response = requests.post(
            url, params=params, auth=(self.username, self.password)
        )
        if response.status_code == 201:
            logger.info("✅ Bridge recording started")
        else:
            logger.warning(
                "⚠️ Ошибка записи моста: %s - %s", response.status_code, response.text
            )

    def originate_channel(
        self, endpoint: str, app: str, format: str = "slin16"
    ) -> str | None:
        """
        Originate a channel.
        Args:
            endpoint (str): The endpoint to originate the channel to.
            app (str): The application name.
            format (str): Audio format to use.
        """
        url = f"http://{self.host}:{self.port}/ari/channels"
        data = {
            "endpoint": endpoint,
            "app": app,
            # "formats": format,
        }
        logger.info("URL: %s", url)
        logger.info("Data: %s", data)
        response = requests.post(url, json=data, auth=(self.username, self.password))
        if response.status_code == 200:
            logger.info("✅ Channel originated")
            return response.json().get("id")
        else:
            logger.warning(
                "⚠️ Ошибка originate: %s - %s", response.status_code, response.text
            )
            return None
