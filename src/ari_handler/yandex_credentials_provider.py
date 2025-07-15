import logging
import time

import aiohttp
import jwt
import requests
from yandex_settings import YandexSettings

logger = logging.getLogger(__name__)


class YandexCredentialsProvider:

    def __init__(self, settings: YandexSettings):
        self.service_account_id = settings.service_account_id
        self.key_id = settings.sa_key_id
        self.private_key = settings.private_key
        self.folder_id = settings.folder_id

    async def get_iam_token(self) -> str:
        logger.info("Getting IAM token")
        jwt_token = self._generate_jwt()
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://iam.api.cloud.yandex.net/iam/v1/tokens",
                json={"jwt": jwt_token},
            ) as resp:
                data = await resp.json()
                token = data["iamToken"]
                return token

    def _generate_jwt(self) -> str:
        logger.info("Generating JWT")
        now = int(time.time())
        payload = {
            "aud": "https://iam.api.cloud.yandex.net/iam/v1/tokens",
            "iss": self.service_account_id,
            "iat": now,
            "exp": now + 360,
            "kid": self.key_id,
        }

        try:
            token = jwt.encode(
                payload,
                self.private_key,
                algorithm="PS256",
                headers={"kid": self.key_id},
            )
            logger.info("JWT token successfully generated")
            return token
        except Exception as e:
            logger.exception("❌ Failed to generate JWT token: %s", e)
            raise


if __name__ == "__main__":
    import asyncio

    settings = YandexSettings()
    provider = YandexCredentialsProvider(settings)
    token = asyncio.run(provider.get_iam_token())
    print(token)
