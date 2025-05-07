import asyncio
import asyncari

from .ari_client import AriClient

AST_HOST = "localhost"
AST_PORT = 8088
AST_URL = f"http://{AST_HOST}:{AST_PORT}/"
AST_APP = "voicebot"
AST_USER = "ariuser"
AST_PASS = "ariuser"


async def on_start(client):
    print("🎧 Слушаем вызовы")
    async with client.on_channel_event('StasisStart') as listener:
        async for objs, event in listener:
            channel = objs['channel']
            await channel.answer()
            print(f"📞 Входящий звонок от {channel.caller['number']}")

            # TODO: Транслировать звонок на localhost:4000/udp
            # bridge = await client.bridges.create(type='mixing')
            # await bridge.addChannel(channel=channel.id)

            # external = await client.channels.originate(
            #     endpoint='external/voicebot',  # 'external/' говорит Asterisk, что это external media
            #     app='voicebot',
            #     appArgs='external',
            #     format='ulaw',
            #     transport='udp',
            #     ip='127.0.0.1',
            #     port=4000
            # )
            # external.wait_for_state('Up')
            # bridge.addChannel(channel=external.id)

            # ari_client = AriClient(AST_HOST, AST_PORT)
            # new_channel_id = ari_client.originate_channel(
            #     endpoint="PJSIP/udpendpoint",
            #     app=AST_APP,
            #     format='slin16',
            # )
            # if new_channel_id:
            #     await bridge.addChannel(channel=new_channel_id)

            print("🎧 Подключён к внешнему потоку, запускай TTS стример")


async def create_external_media(channel_id):
    ari_client = AriClient(AST_HOST, AST_PORT)
    ari_client.channels_external_media(
        channel_id=channel_id,
        app=AST_APP,
        external_host='localhost:4000/udp',
        format='slin16',
    )


async def start():
    async with asyncari.connect(AST_URL, AST_APP, AST_USER, AST_PASS) as client:
        client.taskgroup.start_soon(on_start, client)
        # Run the WebSocket
        async for m in client:
            print("** EVENT **", m)


if __name__ == "__main__":
    asyncio.run(start())
