import asyncio
import grpc

from yandex_credentials_provider import YandexCredentialsProvider
from yandex_settings import YandexSettings
from generated import tts_service_pb2_grpc
from generated.yandex.cloud.ai.tts.v3 import tts_pb2
from speech_synthesizer import SpeechSynthesizer
from audio_converter import AudioConverter


class YandexSpeechSynthesizer(SpeechSynthesizer):
    """
    Yandex Speech Synthesizer.
    """

    def __init__(self, credentials_provider: YandexCredentialsProvider):
        """
        Initialize the YandexSpeechSynthesizer.

        :param credentials_provider: YandexCredentialsProvider instance.
        """
        self.credentials_provider = credentials_provider
        self.channel = grpc.secure_channel(
            "tts.api.cloud.yandex.net:443",
            grpc.ssl_channel_credentials()
        )
        self.stub = tts_service_pb2_grpc.SynthesizerStub(self.channel)

    def _synthesize_sync(self, text: str, iam_token: str) -> bytes:
        """
        Synthesize text to audio using Yandex Speechkit.

        :param text: Text to synthesize.
        :param iam_token: IAM token.
        :return: Audio data in u-law format.
        """
        request = tts_pb2.UtteranceSynthesisRequest(
            text=text,
            output_audio_spec=tts_pb2.AudioFormatOptions(
                container_audio=tts_pb2.ContainerAudio(
                    container_audio_type=tts_pb2.ContainerAudio.OGG_OPUS
                )
            ),
            hints=[tts_pb2.Hints(voice="alena")],
        )

        print("🔥 Sending request...")

        try:
            response_stream = self.stub.UtteranceSynthesis(
                request,
                metadata=[
                    ("authorization", f"Bearer {iam_token}"),
                    ("x-folder-id", self.credentials_provider.folder_id),
                ],
            )

            audio_chunks = []
            for response in response_stream:
                if response.HasField("audio_chunk"):
                    audio_chunks.append(response.audio_chunk.data)

            return AudioConverter.ogg_opus_to_ulaw(b"".join(audio_chunks))

        except grpc.RpcError as e:
            print("🚨 gRPC ERROR")
            print(f"🧾 Code: {e.code()}")
            print(f"🗒 Details: {e.details()}")
            raise

    async def synthesize(self, text: str) -> bytes:
        iam_token = await self.credentials_provider.get_iam_token()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._synthesize_sync, text, iam_token)


if __name__ == "__main__":
    settings = YandexSettings()
    credentials_provider = YandexCredentialsProvider(settings)
    synthesizer = YandexSpeechSynthesizer(credentials_provider)

    audio = asyncio.run(synthesizer.synthesize("Привет!"))
    with open("output.ulaw", "wb") as f:
        f.write(audio)
