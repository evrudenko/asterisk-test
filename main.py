import asyncio

from ari_handler import start

async def main():
    await start()

if __name__ == "__main__":
    asyncio.run(main())
