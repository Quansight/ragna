import asyncio
import inspect
import random
import uuid
from pathlib import Path
from typing import Annotated, Any, get_type_hints

import fast_html as f7l
import sse_starlette
from fastapi import APIRouter, BackgroundTasks, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


class FastHtmlResponse(HTMLResponse):
    def render(self, content: Any) -> bytes:
        return f7l.render(content).encode()


router = APIRouter(default_response_class=FastHtmlResponse)


import functools


class Templates(Jinja2Templates):
    def __call__(self, template_name: str):
        def decorator(endpoint):
            # The template response requires the request as input. If it not is not
            # required by the endpoint, we add it to the signature for it to be supplied
            # automatically by FastAPI.
            signature = inspect.signature(endpoint)
            parameters = list(signature.parameters.values())
            for name, annotation in get_type_hints(endpoint).items():
                if isinstance(annotation, type) and issubclass(annotation, Request):
                    request_name, forward_request = name, True
                    break
            else:
                request_name, forward_request = "__request__", False
                parameters.append(
                    inspect.Parameter(
                        name=request_name,
                        kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        annotation=Request,
                    )
                )
            signature = signature.replace(parameters=parameters)

            @functools.wraps(endpoint)
            async def wrapper(**values):
                request = values[request_name]
                if not forward_request:
                    del values[request_name]

                context = endpoint(**values)
                if inspect.isawaitable(context):
                    context = await context
                if context is None:
                    context = {}

                context["request"] = request
                return self.TemplateResponse(template_name, context)

            wrapper.__signature__ = signature

            return wrapper

        return decorator


templates = Templates(directory=Path(__file__).parent / "templates")


def common_parameters(request: "Request"):
    print(request)
    return {"a": "b"}


@router.get("/")
@templates("index.html")
def index():
    pass


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


@router.post("/answer")
async def answer(prompt: Annotated[str, Form()], background_tasks: BackgroundTasks):
    answer_id = str(uuid.uuid4())
    background_tasks.add_task(get_answer, prompt, answer_id)
    return [
        f7l.div([f7l.b("User: "), prompt], id=str(uuid.uuid4())),
        f7l.div(
            f7l.b("Assistant: "),
            id=answer_id,
            sse_swap=answer_id,
            hx_swap="beforeend",
        ),
    ]


async def get_answer(prompt, id):
    async for chunk in assistant(prompt):
        await EVENTS.put({"event": id, "data": chunk})


import string


async def assistant(prompt):
    await asyncio.sleep(random.uniform(0, 1))
    for c in string.ascii_letters:
        await asyncio.sleep(random.uniform(0, 200e-3))
        yield c


EVENTS: asyncio.Queue = None


@router.get("/events")
async def events():
    global EVENTS
    EVENTS = asyncio.Queue()

    async def event_stream():
        while True:
            event = await EVENTS.get()
            yield event

    return sse_starlette.EventSourceResponse(event_stream())
