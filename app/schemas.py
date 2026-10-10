from datetime import datetime
from pydantic import BaseModel, ConfigDict


class RoomCreate(BaseModel):
    context_type: str  # "listing" or "trade"
    context_id: int


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    context_type: str
    context_id: int
    created_at: datetime


class MessageCreate(BaseModel):
    sender_id: int
    body: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    sender_id: int
    body: str
    created_at: datetime