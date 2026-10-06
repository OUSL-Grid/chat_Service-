import asyncio
import json

import websockets

ROOM_ID = 1
BASE = "ws://127.0.0.1:8000/ws/rooms"


async def listen(name: str, ws):
    """Print every message this user receives."""
    try:
        async for raw in ws:
            msg = json.loads(raw)
            print(f"[{name} received] user {msg['sender_id']} said: {msg['body']}")
    except websockets.ConnectionClosed:
        pass


async def main():
    # Open one connection per user (this is the "phone call")
    async with websockets.connect(f"{BASE}/{ROOM_ID}?user_id=1") as alice, \
               websockets.connect(f"{BASE}/{ROOM_ID}?user_id=2") as bob:

        # Start both users listening in the background
        alice_task = asyncio.create_task(listen("User 1", alice))
        bob_task = asyncio.create_task(listen("User 2", bob))

        # User 1 talks
        await alice.send("Hi, is the book still available?")
        await asyncio.sleep(0.5)

        # User 2 replies
        await bob.send("Yes it is! Want to meet at the library?")
        await asyncio.sleep(0.5)

        # User 1 answers
        await alice.send("Perfect, see you at 3pm.")
        await asyncio.sleep(0.5)

        alice_task.cancel()
        bob_task.cancel()


asyncio.run(main())