import asyncio
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
    """Application settings/configurations"""

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


# Setting object
settings = Settings()


class WebSocketConnectionManager:
    def __init__(self) -> None:
        """Initial connection manager with active_connections list"""
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """handle connecting request

        Args:
            websocket (WebSocket): websocket object to store in active_connections list
        """
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Handle disconnecting request

        Args:
            websocket (WebSocket): websocket object to remove from active_connections list
        """
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        """broadcasting a message to every active_connections

        Args:
            message (str): the message to be broadcasted
        """
        _, true_votes, false_votes, create_ts = message.split("|")
        true_votes = int(true_votes)
        false_votes = int(false_votes)
        total_votes = true_votes + false_votes
        true_vote_perc = 100 * true_votes / total_votes
        false_vote_perc = 100 * false_votes / total_votes
        for connection in self.active_connections:
            formatted_msg = templates.get_template("result_response.html").render(
                {
                    "timestamp": create_ts,
                    "total_votes": total_votes,
                    "true_vote_perc": true_vote_perc,
                    "false_vote_perc": false_vote_perc,
                }
            )
            await connection.send_text(formatted_msg)


# Websocket connection manager object
ws_conn_manager = WebSocketConnectionManager()


class CustomWebSocketEndpoint(WebSocketEndpoint):
    """Websocket Endpoint to customize handling events"""

    async def on_connect(self, websocket: WebSocket, **kwargs):
        """handle in comming connection

        Args:
            websocket (WebSocket): websocket connection object
        """
        await ws_conn_manager.connect(websocket)

        self.task = asyncio.create_task(self.send_events(websocket))

    async def send_events(self, websocket: WebSocket):
        """A task to keep websocket endpoint active

        Args:
            websocket (WebSocket): websocket connection object
        """
        await asyncio.Future()

    async def on_disconnect(self, websocket: WebSocket, close_code: int):
        """Handle a disconnecting websocket

        Args:
            websocket (WebSocket): websocket connection object
            close_code (int): code of closing connection
        """
        self.task.cancel()
        ws_conn_manager.disconnect(websocket)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle open and close of database connection when app startup and shutdown

    Args:
        app (FastAPI): FastAPI app object

    Yields:
        dict: database connection
    """
    db_connection = await asyncpg.connect(
        f"postgresql://{settings.DB_USERNAME}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )

    async def broadcast_message(*args):
        connection, pid, channel, payload = args
        await ws_conn_manager.broadcast(payload)

    await db_connection.add_listener("new_result", broadcast_message)

    yield {"db_connection": db_connection}

    await db_connection.close()


# create FastAPI app object, with custom lifespan and websocket route to custom websocket endpoint
app = FastAPI(
    lifespan=lifespan,
    routes=(WebSocketRoute("/result", CustomWebSocketEndpoint, name="ws"),),
)

# mount to static directory to serve static files
app.mount("/static", StaticFiles(directory="src/voting_app/static"), name="static")

# jinja templates for responses
templates = Jinja2Templates(directory="src/voting_app/templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Homepage

    Args:
        request (Request): Request object
    """
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.get("/result/latest", response_class=HTMLResponse)
async def get_latest_result(request: Request):
    """Get latest result

    Args:
        request (Request): Request object
    """
    row = await request.state.db_connection.fetchrow(
        """SELECT
            *
        FROM
            results r
        WHERE
            r.id = (
            SELECT
                max(id)
            FROM
                results r2)
        """
    )
    true_votes = row["vote_true"]
    false_votes = row["vote_false"]
    created_ts = row["created_at"]
    total_votes = true_votes + false_votes
    true_vote_perc = 100 * true_votes / total_votes
    false_vote_perc = 100 * false_votes / total_votes

    return templates.TemplateResponse(
        request=request,
        name="result_response.html",
        context={
            "timestamp": created_ts,
            "total_votes": total_votes,
            "true_vote_perc": true_vote_perc,
            "false_vote_perc": false_vote_perc,
        },
    )


@app.post("/vote/{id}", response_class=HTMLResponse)
async def vote(request: Request, id: int):
    """Voting api

    Args:
        request (Request): Request object
        id (int): vote value
    """
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

    uvicorn.run(app, ws_ping_interval=20, ws_ping_timeout=20)
