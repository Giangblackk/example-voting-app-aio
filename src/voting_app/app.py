import asyncio
from contextlib import asynccontextmanager
from typing import List

import asyncpg
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

result_queue = asyncio.Queue()


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn: asyncpg.connection.Connection = await asyncpg.connect(
        "postgresql://postgres:changemetoyoupassword@localhost/postgres"
    )

    def result_queue_put(*args):
        connection, pid, channel, payload = args
        result_queue.put_nowait(payload)

    await conn.add_listener("new_result", result_queue_put)

    yield

    await conn.close()


app = FastAPI(lifespan=lifespan)


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()

app.mount("/static", StaticFiles(directory="src/voting_app/static"), name="static")
templates = Jinja2Templates(directory="src/voting_app/templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.get("/vote/{id}", response_class=HTMLResponse)
async def vote(request: Request, id: int):
    return templates.TemplateResponse(
        request=request,
        name="vote_response.html",
        context={"vote_value": "left" if id == 0 else "right"},
    )


@app.websocket("/result")
async def websocket_result(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            message = await result_queue.get()
            await manager.broadcast(message)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
