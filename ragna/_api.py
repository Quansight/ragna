import functools
import uuid

from traceback import format_exception

from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException

from pydantic import BaseModel, Field, HttpUrl

from ragna.core import Chat, LocalDocument, MessageRole, Rag, RagnaException


class DocumentModel(BaseModel):
    id: UUID
    name: str


class UploadData(BaseModel):
    token: str


class DocumentUploadInfoModel(BaseModel):
    url: HttpUrl
    data: UploadData
    document: DocumentModel


class SourceModel(BaseModel):
    id: UUID
    document_id: UUID
    document_name: str
    location: str

    @classmethod
    def _from_source(cls, source):
        return cls(
            id=source.id,
            document_id=source.document_id,
            document_name=source.document_name,
            location=source.location,
        )


class MessageModel(BaseModel):
    id: UUID
    role: MessageRole
    content: str
    sources: list[SourceModel]

    @classmethod
    def _from_message(cls, message):
        return cls(
            id=message.id, role=message.role, content=message.content, sources=[]
        )


class ChatMetadataModel(BaseModel):
    name: str
    document_ids: list[UUID]
    source_storage: str
    assistant: str
    params: dict = Field(default_factory=dict)

    @classmethod
    def _from_chat(cls, chat):
        return cls(
            name=chat.name,
            document_ids=[d.id for d in chat.documents],
            source_storage=str(chat.source_storage),
            assistant=str(chat.assistant),
            params=chat.params,
        )


class ChatModel(BaseModel):
    id: UUID
    metadata: ChatMetadataModel
    messages: list[MessageModel]

    @classmethod
    def _from_chat(cls, chat):
        return cls(
            id=chat.id,
            metadata=ChatMetadataModel._from_chat(chat),
            messages=[MessageModel._from_message(m) for m in chat.messages],
        )


import re


# Can we make this a custom type for the DB? Maybe just subclass from str?
class RagnaId:
    _UUID_STR_PATTERN = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )

    @staticmethod
    def is_valid(obj: Any) -> bool:
        if isinstance(obj, UUID):
            obj = str(obj)
        elif not isinstance(obj, str):
            return False

        return RagnaId._UUID_STR_PATTERN.match(obj) is not None

    @staticmethod
    def from_uuid(uuid: UUID) -> str:
        return str(uuid)

    @staticmethod
    def make():
        return RagnaId.from_uuid(uuid.uuid4())


def process_exception(afn):
    @functools.wraps(afn)
    async def wrapper(*args, **kwargs):
        try:
            return await afn(*args, **kwargs)
        except ():
            raise
        except RagnaException as exc:
            # FIXME: process that here
            raise HTTPException(
                status_code=400, detail="\n".join(format_exception(exc))
            ) from None
        except Exception as exc:
            print(exc)
            raise HTTPException(status_code=500) from None

    return wrapper


def api(**kwargs):
    rag = Rag(**kwargs, start_ragna_worker=False, start_redis_server=False)

    app = FastAPI()

    async def _authorize_user(user: str) -> str:
        # FIXME: implement auth here
        return user

    UserDependency = Annotated[str, Depends(_authorize_user)]

    @app.get("/document/new")
    async def get_document_upload_info(
        user: UserDependency,
        name: str,
    ) -> DocumentUploadInfoModel:
        id = RagnaId.make()
        url, data, metadata = await rag.config.document_class.get_upload_info(
            config=rag.config, user=user, id=id, name=name
        )
        rag._add_document(user=user, id=id, name=name, metadata=metadata)
        return DocumentUploadInfoModel(
            url=url, data=UploadData(**data), document=DocumentModel(id=id, name=name)
        )

    @app.post("/document/upload")
    # @process_exception
    async def upload_document(data: UploadData) -> DocumentModel:
        if not issubclass(rag.config.document_class, LocalDocument):
            raise RagnaException

        user, id = rag.config.document_class._extract_user_and_document_id_from_token(
            data.token
        )
        document = rag._get_document(user=user, id=id)

        document.path.parent.mkdir(parents=True, exist_ok=True)
        with open(document.path, "wb") as file:
            file.write(b"FIXME")

        return DocumentModel(id=id, name=document.name)

    @app.get("/chats")
    async def get_chats(user: UserDependency) -> list[ChatModel]:
        return [ChatModel._from_chat(chat) for chat in await rag._get_chats(user=user)]

    @app.post("/chat/new")
    async def new_chat(
        *, user: UserDependency, chat_metadata: ChatMetadataModel
    ) -> ChatModel:
        return ChatModel._from_chat(
            await rag.new_chat(
                user=user,
                name=chat_metadata.name,
                documents=[RagnaId.from_uuid(u) for u in chat_metadata.document_ids],
                source_storage=chat_metadata.source_storage,
                assistant=chat_metadata.assistant,
                **chat_metadata.params,
            )
        )

    IdDependency = Annotated[str, Depends(RagnaId.from_uuid)]

    async def _get_chat(*, user: UserDependency, id: IdDependency) -> Chat:
        return await rag.get_chat(user=user, id=id)

    ChatDependency = Annotated[Chat, Depends(_get_chat, use_cache=False)]

    @app.get("/chat/{id}")
    async def get_chat(chat: ChatDependency) -> ChatModel:
        return ChatModel._from_chat(chat)

    @app.post("/chat/{id}/start")
    async def start_chat(chat: ChatDependency) -> ChatModel:
        return ChatModel._from_chat(await chat.start())

    @app.post("/chat/{id}/close")
    async def close_chat(chat: ChatDependency) -> ChatModel:
        return ChatModel._from_chat(await chat.close())

    @app.post("/chat/{id}/answer")
    async def answer(chat: ChatDependency, prompt: str) -> MessageModel:
        return MessageModel._from_message(await chat.answer(prompt))

    return app
