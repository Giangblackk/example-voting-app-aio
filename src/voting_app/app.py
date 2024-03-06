import asyncio
import datetime
from contextlib import asynccontextmanager
from typing import List

import asyncpg
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.endpoints import WebSocketEndpoint
from starlette.routing import WebSocketRoute
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_HOST: str = "postgres"
    DB_PORT: int = 5432
    DB_NAME: str = "postgres"
    DB_USERNAME: str = "postgres"
    DB_PASSWORD: str = "changemetoyoupassword"

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()


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
            formatted_msg = templates.get_template("result_response.html").render(
                {"timestamp": datetime.datetime.now(), "message": message}
            )
            await connection.send_text(formatted_msg)


manager = ConnectionManager()


class CustomWebSocketEndpoint(WebSocketEndpoint):
    async def on_connect(self, websocket, **kwargs):
        await manager.connect(websocket)

        self.task = asyncio.create_task(self.send_events(websocket))

    async def send_events(self, websocket):
        await asyncio.Future()

    async def on_disconnect(self, websocket, close_code):
        self.task.cancel()
        manager.disconnect(websocket)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_connection = await asyncpg.connect(
        f"postgresql://{settings.DB_USERNAME}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )

    async def broadcast_message(*args):
        connection, pid, channel, payload = args
        await manager.broadcast(payload)

    await db_connection.add_listener("new_result", broadcast_message)

    yield {"db_connection": db_connection}

    await db_connection.close()


app = FastAPI(
    lifespan=lifespan,
    routes=(WebSocketRoute("/result", CustomWebSocketEndpoint, name="ws"),),
)

app.mount("/static", StaticFiles(directory="src/voting_app/static"), name="static")
templates = Jinja2Templates(directory="src/voting_app/templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.post("/vote/{id}", response_class=HTMLResponse)
async def vote(request: Request, id: int):
    insert_value = True if id == 0 else False
    await request.state.db_connection.execute(
        """
        INSERT INTO votes (vote) VALUES ($1)
    """,
        insert_value,
    )
    return templates.TemplateResponse(
        request=request,
        name="vote_response.html",
        context={"vote_value": "left" if insert_value else "right"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
