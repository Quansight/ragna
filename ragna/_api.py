import contextlib
from typing import Any
from uuid import UUID

from fastapi import FastAPI

from pydantic import BaseModel, Field

from ragna.core import Rag

DEFAULT_USER = "root"


class NewChatData(BaseModel):
    name: str
    documents: list[UUID]
    source_storage: str
    llm: str
    params: dict[str, Any] = Field(default_factory=dict)


def api(**kwargs):
    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.rag = Rag(**kwargs)
        yield

    app = FastAPI(lifespan=lifespan)

    @app.get("/get-chat")
    async def get_chat(*, user: str = DEFAULT_USER, id: UUID):
        pass

    @app.get("/get-chats")
    async def get_chats(*, user: str = DEFAULT_USER):
        # get all chats for user
        pass

    @app.post("/new-chat")
    async def new_chat(*, user: str = DEFAULT_USER, new_chat_data: NewChatData) -> str:
        chat = await app.state.rag.start_new_chat(
            user=user,
            name=new_chat_data.name,
            documents=[str(d) for d in new_chat_data.documents],
            source_storage=new_chat_data.source_storage,
            llm=new_chat_data.llm,
            **new_chat_data.params,
        )
        return chat.id

    @app.post("/start-chat")
    async def start_chat(*, user: str = DEFAULT_USER, id: UUID):
        await app.state.rag.start_chat(user=user, id=id)

    @app.post("/close-chat")
    async def close_chat(*, user: str = DEFAULT_USER, id: UUID):
        pass

    @app.post("/answer")
    async def answer(*, user: str = DEFAULT_USER, chat_id: UUID, prompt: str):
        answer = None
        return {
            "sources": [
                {
                    attr: getattr(source, attr)
                    for attr in ["document_id", "document_name", "page_numbers"]
                }
                for source in answer.sources
            ],
            "content": answer.content,
        }

    return app
