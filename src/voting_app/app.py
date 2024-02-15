import asyncio
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Request, WebSocket
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
    await websocket.accept()
    while True:
        message = await result_queue.get()
        await websocket.send_text(message)
