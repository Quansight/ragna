import asyncio
from typing import Annotated

import sse_starlette
from fastapi import APIRouter, Depends, Form, Request, UploadFile, status
from fastapi.background import BackgroundTasks
from fastapi.responses import HTMLResponse

import ragna.core
from ragna._compat import aiter, anext
from ragna._utils import as_awaitable

from ._session import Session, SessionDependency
from ._templates import TemplateResponse
from ._utils import redirect_response
from .schemas import User


def make_router(engine, config):
    router = APIRouter()

    auth = config.authentication()

    @router.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        return await as_awaitable(auth.login_page, request)

    async def _login(request: Request):
        result = await as_awaitable(auth.login, request)
        if not isinstance(result, User):
            return result

        request.state.session = Session(id=request.state.session_id, user=result)
        return redirect_response(
            "/ui", htmx=request, status_code=status.HTTP_303_SEE_OTHER
        )

    @router.post("/login")
    async def login(request: Request):
        return await _login(request)

    @router.get("/oauth-callback")
    async def oauth_callback(request: Request):
        return await _login(request)

    @router.post("/logout")
    async def logout(request: Request):
        request.state.session = None
        return redirect_response(
            "/ui/login", htmx=request, status_code=status.HTTP_303_SEE_OTHER
        )

    @router.get("")
    async def main_page(request: Request, session: SessionDependency):
        return TemplateResponse(
            name="index.html",
            context={"request": request, "user": session.user},
        )

    event_queues: dict[str, asyncio.Queue] = {}

    async def _get_event_queue(session: SessionDependency) -> asyncio.Queue:
        return event_queues.setdefault(session.id, asyncio.Queue())

    EventQueueDependency = Annotated[asyncio.Queue, Depends(_get_event_queue)]

    @router.get("/events")
    async def events(
        event_queue: EventQueueDependency,
    ) -> sse_starlette.EventSourceResponse:
        async def event_stream():
            while True:
                yield await event_queue.get()

        return sse_starlette.EventSourceResponse(event_stream())

    @router.post("/chat")
    async def upload_documents(
        request: Request, documents: list[UploadFile], chat_name: Annotated[str, Form()]
    ):
        await engine.upload_documents(documents)

    @router.post("/chats/{chat_id}/answer")
    async def answer_prompt(
        background_tasks: BackgroundTasks,
        session: SessionDependency,
        event_queue: EventQueueDependency,
        prompt: Annotated[str, Form()],
    ):
        message = await engine.answer_prompt(
            user=session.user.username, chat_id=session.current_chat_id, prompt=prompt
        )
        background_tasks.add_task(_stream_answer, event_queue, message)
        # return HTML HERE

    async def _stream_answer(
        event_queue: asyncio.Queue, message: ragna.core.Message
    ) -> None:
        stream = aiter(message)
        chunk = anext(stream)
        await event_queue.put(
            {
                "event": message.id,
                "data": "html that replaces the old placeholder with beforeend",
            }
        )

        async for chunk in stream:
            await event_queue.put({"event": message.id, "data": chunk})

    # Send system message -> just the message template
    # Send user message -> just the message template
    # Send assistant placeholder -> message with extra attributes
    # Send assistant first chunk -> message with extra attributes

    return router
