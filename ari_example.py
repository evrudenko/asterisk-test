import os
import asyncari
from asyncari.state import ToplevelChannelState, DTMFHandler
import anyio
import logging
from httpx import HTTPStatusError


ast_host = os.getenv("AST_HOST", 'localhost')
ast_port = int(os.getenv("AST_ARI_PORT", 8088))
ast_url = os.getenv("AST_URL", 'http://%s:%d/'%(ast_host,ast_port))
ast_username = os.getenv("AST_USER", 'ariuser')
ast_password = os.getenv("AST_PASS", 'ariuser')
ast_app = os.getenv("AST_APP", 'voicebot')


class State(ToplevelChannelState, DTMFHandler):
    do_hang = False

    async def on_start(self):
        await self.channel.play(media='sound:hello')

    async def on_dtmf_Star(self, evt):
        self.do_hang = True
        await self.channel.play(media='sound:vm-goodbye')

    async def on_dtmf_Pound(self, evt):
        await self.channel.play(media='sound:asterisk-friend')

    async def on_dtmf(self, evt):
        await self.channel.play(media='sound:digits/%s' % evt.digit)

    async def on_PlaybackFinished(self, evt):
        if self.do_hang:
            try:
                await self.channel.continueInDialplan()
            except HTTPStatusError:
                pass
        
async def on_start(client):
    
    """Callback for StasisStart events.

    On new channels, register the on_dtmf callback, answer the channel and
    play "Hello, world"

    :param channel: Channel DTMF was received from.
    :param event: Event.
    """
    async with client.on_channel_event('StasisStart') as listener:
        async for objs, event in listener:
            channel = objs['channel']

            bridge = await client.bridges.create(type='mixing')
            await bridge.addChannel(channel=channel.id)

            await client.bridges[bridge.id].externalMedia(
                app=ast_app,
                external_host='127.0.0.1:4000/udp',
                format='slin16'
            )

            await channel.answer()
            client.taskgroup.start_soon(State(channel).start_task)

async def main():
    async with asyncari.connect(ast_url, ast_app, ast_username,ast_password) as client:
        client.taskgroup.start_soon(on_start, client)
        # Run the WebSocket
        async for m in client:
            print("** EVENT **", m)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    try:
        anyio.run(main)
    except KeyboardInterrupt:
        pass
