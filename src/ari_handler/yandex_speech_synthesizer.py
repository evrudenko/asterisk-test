import asyncio
import logging

import grpc
from audio_converter import AudioConverter
from speech_synthesizer import SpeechSynthesizer
from yandex_credentials_provider import YandexCredentialsProvider
from yandex_settings import YandexSettings

from generated import tts_service_pb2_grpc
from generated.yandex.cloud.ai.tts.v3 import tts_pb2

logger = logging.getLogger(__name__)


class YandexSpeechSynthesizer(SpeechSynthesizer):
    """
    Fully async Yandex Speech Synthesizer using gRPC aio.
    """

    def __init__(self, credentials_provider: YandexCredentialsProvider):
        """
        Initialize the YandexSpeechSynthesizer with the given credentials provider.

        :param credentials_provider: Instance of YandexCredentialsProvider to manage IAM tokens.
        """
        self.credentials_provider = credentials_provider
        self.iam_token = None

    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize speech asynchronously using Yandex TTS gRPC API.

        :param text: Text to synthesize.
        :return: Audio data in u-law format.
        """
        logger.info("🔥 Synthesizing text: %s", text)
        if not self.iam_token:
            self.iam_token = await self.credentials_provider.get_iam_token()

        request = tts_pb2.UtteranceSynthesisRequest(
            text=text,
            output_audio_spec=tts_pb2.AudioFormatOptions(
                container_audio=tts_pb2.ContainerAudio(
                    container_audio_type=tts_pb2.ContainerAudio.OGG_OPUS
                )
            ),
            hints=[tts_pb2.Hints(voice="alena")],
        )

        metadata = [
            ("authorization", f"Bearer {self.iam_token}"),
            ("x-folder-id", self.credentials_provider.folder_id),
        ]

        # ✅ Канал создаётся внутри текущего event loop
        async with grpc.aio.secure_channel(
            "tts.api.cloud.yandex.net:443", grpc.ssl_channel_credentials()
        ) as channel:
            stub = tts_service_pb2_grpc.SynthesizerStub(channel)
            try:
                response_stream = stub.UtteranceSynthesis(request, metadata=metadata)
                audio_chunks = []
                async for response in response_stream:
                    if response.HasField("audio_chunk"):
                        audio_chunks.append(response.audio_chunk.data)

                audio_response = b"".join(audio_chunks)
                logger.info("✅ Synthesis completed successfully")
                ulaw_response = await AudioConverter.ogg_opus_to_ulaw(audio_response)
                logger.info("✅ Audio converted to u-law format")
                return ulaw_response

            except grpc.aio.AioRpcError as e:
                logger.error("❌ gRPC error during synthesis: %s", e)
                raise


if __name__ == "__main__":
    settings = YandexSettings()
    credentials_provider = YandexCredentialsProvider(settings)
    synthesizer = YandexSpeechSynthesizer(credentials_provider)

    audio = asyncio.run(synthesizer.synthesize("Пока!"))
    with open("output.ulaw", "wb") as f:
        f.write(audio)
