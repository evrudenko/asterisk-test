import asyncio
import logging
from typing import Optional

import grpc
from audio_converter import AudioConverter
from speech_recognizer import SpeechRecognizer
from yandex_credentials_provider import YandexCredentialsProvider

from generated import stt_service_pb2_grpc as stt_grpc
from generated.yandex.cloud.ai.stt.v3 import stt_pb2 as stt_messages

logger = logging.getLogger(__name__)


class YandexSpeechRecognizer(SpeechRecognizer):
    """
    Fully async Yandex STT Recognizer using gRPC aio.
    """

    def __init__(self, credentials_provider: YandexCredentialsProvider):
        self.credentials_provider = credentials_provider
        self.iam_token = None

    async def recognize(self, ulaw_data: bytes) -> Optional[str]:
        logger.info("🎙️ Starting STT recognition")

        if not self.iam_token:
            self.iam_token = await self.credentials_provider.get_iam_token()

        pcm_data = await AudioConverter.ulaw_to_pcm(ulaw_data)

        metadata = [
            ("authorization", f"Bearer {self.iam_token}"),
            ("x-folder-id", self.credentials_provider.folder_id),
        ]

        async def request_iterator():
            # Session config: one-time initial message
            yield stt_messages.StreamingRequest(
                session_options=stt_messages.StreamingOptions(
                    recognition_model=stt_messages.RecognitionModelOptions(
                        model="general",
                        audio_format=stt_messages.AudioFormatOptions(
                            raw_audio=stt_messages.RawAudio(
                                audio_encoding=stt_messages.RawAudio.LINEAR16_PCM,
                                sample_rate_hertz=8000,
                                audio_channel_count=1,
                            )
                        ),
                    )
                )
            )

            # Send audio in chunks
            chunk_size = 4000
            for i in range(0, len(pcm_data), chunk_size):
                yield stt_messages.StreamingRequest(
                    chunk=stt_messages.AudioChunk(data=pcm_data[i : i + chunk_size])
                )

        async with grpc.aio.secure_channel(
            "stt.api.cloud.yandex.net:443", grpc.ssl_channel_credentials()
        ) as channel:
            stub = stt_grpc.RecognizerStub(channel)

            try:
                response_stream = stub.RecognizeStreaming(
                    request_iterator(), metadata=metadata
                )

                results = []
                async for response in response_stream:
                    if response.HasField("final"):
                        for alt in response.final.alternatives:
                            results.append(alt.text)

                text = " ".join(results).strip()
                logger.info("✅ Recognized: %s", text)
                return text or None

            except grpc.aio.AioRpcError as e:
                logger.error("❌ STT error: %s", e)
                return None


if __name__ == "__main__":
    import asyncio

    from yandex_credentials_provider import YandexCredentialsProvider
    from yandex_settings import YandexSettings

    settings = YandexSettings()
    credentials_provider = YandexCredentialsProvider(settings)
    recognizer = YandexSpeechRecognizer(credentials_provider)

    with open("output.ulaw", "rb") as f:
        ulaw_data = f.read()

    text = asyncio.run(recognizer.recognize(ulaw_data))
    print(f"Recognized text: {text}")
