from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

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
