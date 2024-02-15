import asyncio

import websockets


async def receiver():
    uri = "ws://localhost:8000/result"
    async with websockets.connect(uri) as ws:
        while True:
            msg = await ws.recv()
            print(f"<<< {msg}")


if __name__ == "__main__":
    asyncio.run(receiver())
