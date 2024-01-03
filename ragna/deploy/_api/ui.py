import asyncio
from pathlib import Path
from typing import Annotated, Any

import fast_html as f7l
import sse_starlette
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


class FastHtmlResponse(HTMLResponse):
    def render(self, content: Any) -> bytes:
        return f7l.render(content).encode()


router = APIRouter(default_response_class=FastHtmlResponse)

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@router.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/clicked")
def clicked():
    return f7l.h1("Worked!")


@router.get("/chats")
def chats():
    return f7l.div(
        [
            f7l.div("system message", class_="message message-system"),
            f7l.div("user message", class_="message message-user"),
            f7l.div("assistant message", class_="message message-assistant"),
        ],
        class_="chat-feed",
    )


@router.post("/messages")
async def messages(prompt: Annotated[str, Form()]):
    return f7l.p(f"You asked: {prompt}")


@router.get("/event-source")
async def stream():
    async def gen():
        message = ""
        for chunk in ["foo", "bar", "baz"]:
            await asyncio.sleep(1)
            message += chunk
            yield sse_starlette.ServerSentEvent(data=f7l.render(f7l.p(message)))

    return sse_starlette.EventSourceResponse(gen())
