from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal
from app.models import ChatRoom, Message
from app.schemas import RoomCreate, RoomOut, MessageCreate, MessageOut

app = FastAPI(title="Chat Service")


async def get_db():
    async with SessionLocal() as session:
        yield session


# ---------- NEW: connection manager ----------
class ConnectionManager:
    def __init__(self):
        # Example: {1: [socket_of_user_1, socket_of_user_2]}
        self.rooms: dict[int, list[WebSocket]] = {}

    def add(self, room_id: int, websocket: WebSocket):
        self.rooms.setdefault(room_id, []).append(websocket)

    def remove(self, room_id: int, websocket: WebSocket):
        if room_id in self.rooms and websocket in self.rooms[room_id]:
            self.rooms[room_id].remove(websocket)
            if not self.rooms[room_id]:
                del self.rooms[room_id]

    async def broadcast(self, room_id: int, data: dict):
        for websocket in list(self.rooms.get(room_id, [])):
            await websocket.send_json(data)


manager = ConnectionManager()
# ---------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/rooms", response_model=RoomOut)
async def create_room(data: RoomCreate, db: AsyncSession = Depends(get_db)):
    room = ChatRoom(context_type=data.context_type, context_id=data.context_id)
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room


@app.post("/rooms/{room_id}/messages", response_model=MessageOut)
async def send_message(
    room_id: int, data: MessageCreate, db: AsyncSession = Depends(get_db)
):
    room = await db.get(ChatRoom, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")

    message = Message(room_id=room_id, sender_id=data.sender_id, body=data.body)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


@app.get("/rooms/{room_id}/messages", response_model=list[MessageOut])
async def get_messages(room_id: int, db: AsyncSession = Depends(get_db)):
    room = await db.get(ChatRoom, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")

    result = await db.execute(
        select(Message).where(Message.room_id == room_id).order_by(Message.id)
    )
    return result.scalars().all()


# ---------- NEW: WebSocket endpoint ----------
@app.websocket("/ws/rooms/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: int, user_id: int):
    await websocket.accept()

    # Check that the room exists before letting the user in
    async with SessionLocal() as db:
        room = await db.get(ChatRoom, room_id)
    if room is None:
        await websocket.close(code=4404, reason="Room not found")
        return

    manager.add(room_id, websocket)
    try:
        while True:
            text = await websocket.receive_text()

            # 1. Save to the database
            async with SessionLocal() as db:
                message = Message(room_id=room_id, sender_id=user_id, body=text)
                db.add(message)
                await db.commit()
                await db.refresh(message)
                payload = MessageOut.model_validate(message).model_dump(mode="json")

            # 2. Send to everyone in the room
            await manager.broadcast(room_id, payload)
    except WebSocketDisconnect:
        manager.remove(room_id, websocket)
# ---------------------------------------------