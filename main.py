from enum import IntEnum

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status, HTTPException
from pydantic import BaseModel
from uuid import uuid4
import redis
import os

class Symbol(IntEnum):
    DOT = 0
    DASH = 1

class AuthInfo(BaseModel):
    device_uid: str
    auth_token: str


class MessageRequest(BaseModel):
    auth: AuthInfo
    symbol: Symbol


app = FastAPI()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
redis_client = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/send_message")
async def send_message(request: MessageRequest):
    cached_auth_token = redis_client.get(request.auth.device_uid)
    if not cached_auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Device not registered")
    
    if cached_auth_token != request.auth.auth_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token")

    await manager.broadcast({"symbol": request.symbol.name, "value": request.symbol.value})
    return {"status": "Message broadcasted"}

@app.get("/register_device")
async def register_device():
    device_uid = str(uuid4())
    auth_token = str(uuid4())
    redis_client.set(device_uid, auth_token, ex=1800)
    return {"device_uid": device_uid, "auth_token": auth_token}