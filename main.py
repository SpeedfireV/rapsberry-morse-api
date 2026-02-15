from enum import IntEnum
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

class Symbol(IntEnum):
    DOT = 0
    DASH = 1

class MessageRequest(BaseModel):
    symbol: Symbol

app = FastAPI()


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
    await manager.broadcast({"symbol": request.symbol.name, "value": request.symbol.value})
    return {"status": "Message broadcasted"}