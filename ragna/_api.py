import datetime
import functools
from typing import Annotated
from uuid import UUID

import aiofiles
from fastapi import Depends, FastAPI, Form, HTTPException, UploadFile

from pydantic import BaseModel, Field, HttpUrl, validator

import ragna

from ragna.core import Chat, LocalDocument, MessageRole, RagnaException, RagnaId


class DocumentModel(BaseModel):
    id: RagnaId
    name: str


class DocumentUploadInfoModel(BaseModel):
    url: HttpUrl
    data: dict
    document: DocumentModel


class SourceModel(BaseModel):
    document_id: RagnaId
    document_name: str
    location: str

    @classmethod
    def from_source(cls, source):
        return cls(
            id=source.id,
            document_id=source.document_id,
            document_name=source.document_name,
            location=source.location,
        )


class MessageModel(BaseModel):
    id: RagnaId
    role: MessageRole
    content: str
    sources: list[SourceModel]
    timestamp: datetime.datetime

    @classmethod
    def from_message(cls, message):
        return cls(
            id=message.id,
            role=message.role,
            content=message.content,
            sources=[SourceModel.from_source(s) for s in message.sources],
            timestamp=message.timestamp,
        )


class ChatMetadataModel(BaseModel):
    name: str
    # For some reason list[RagnaId] does not work and will get parsed into list[UUID].
    # Thus, we use a validator below to do the conversion.
    document_ids: list[UUID]
    source_storage: str
    assistant: str
    params: dict = Field(default_factory=dict)

    @validator("document_ids")
    def uuid_to_ragna_id(cls, document_ids: list[UUID]) -> list[RagnaId]:
        return [RagnaId.from_uuid(u) for u in document_ids]

    @classmethod
    def from_chat(cls, chat):
        return cls(
            name=chat.name,
            document_ids=[d.id for d in chat.documents],
            source_storage=str(chat.source_storage),
            assistant=str(chat.assistant),
            params=chat.params,
        )


class ChatModel(BaseModel):
    id: RagnaId
    metadata: ChatMetadataModel
    messages: list[MessageModel]
    started: bool
    closed: bool

    @classmethod
    def from_chat(cls, chat):
        return cls(
            id=chat.id,
            metadata=ChatMetadataModel.from_chat(chat),
            messages=[MessageModel.from_message(m) for m in chat.messages],
            started=chat._started,
            closed=chat._closed,
        )


class AnswerOutputModel(BaseModel):
    message: MessageModel
    chat: ChatModel


class ComponentsModel(BaseModel):
    source_storages: list[str]
    assistants: list[str]


def process_ragna_exception(afn):
    @functools.wraps(afn)
    async def wrapper(*args, **kwargs):
        try:
            return await afn(*args, **kwargs)
        except RagnaException as exc:
            if exc.http_detail is RagnaException.EVENT:
                detail = exc.event
            elif exc.http_detail is RagnaException.MESSAGE:
                detail = str(exc)
            else:
                detail = exc.http_detail
            raise HTTPException(
                status_code=exc.http_status_code, detail=detail
            ) from None
        except Exception:
            raise

    return wrapper


def api(rag):
    app = FastAPI()

    @app.get("/health")
    @process_ragna_exception
    async def health() -> str:
        return ragna.__version__

    async def _authorize_user(user: str) -> str:
        # FIXME: implement auth here
        return user

    UserDependency = Annotated[str, Depends(_authorize_user)]

    @app.get("/chats")
    @process_ragna_exception
    async def get_chats(user: UserDependency) -> list[ChatModel]:
        return [ChatModel.from_chat(chat) for chat in rag._get_chats(user=user)]

    @app.get("/components")
    @process_ragna_exception
    async def get_components(_: UserDependency) -> ComponentsModel:
        return ComponentsModel(
            source_storages=list(rag.config.registered_source_storage_classes),
            assistants=list(rag.config.registered_assistant_classes),
        )

    @app.get("/document/new")
    @process_ragna_exception
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
            url=url, data=data, document=DocumentModel(id=id, name=name)
        )

    @app.post("/document/upload")
    @process_ragna_exception
    async def upload_document(
        token: Annotated[str, Form()], file: UploadFile
    ) -> DocumentModel:
        if not issubclass(rag.config.document_class, LocalDocument):
            raise HTTPException(
                status_code=400,
                detail="Ragna configuration does not support local upload",
            )

        user, id = rag.config.document_class._decode_upload_token(
            token, secret=rag.config.upload_token_secret
        )
        document = rag._get_document(user=user, id=id)

        document.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(document.path, "wb") as document_file:
            while content := await file.read(1024):
                await document_file.write(content)

        return DocumentModel(id=id, name=document.name)

    @app.post("/chat/new")
    @process_ragna_exception
    async def new_chat(
        *, user: UserDependency, chat_metadata: ChatMetadataModel
    ) -> ChatModel:
        return ChatModel.from_chat(
            await rag.new_chat(
                user=user,
                name=chat_metadata.name,
                documents=chat_metadata.document_ids,
                source_storage=chat_metadata.source_storage,
                assistant=chat_metadata.assistant,
                **chat_metadata.params,
            )
        )

    async def _get_id(id: UUID) -> RagnaId:
        return RagnaId.from_uuid(id)

    IdDependency = Annotated[RagnaId, Depends(_get_id)]

    async def _get_chat(*, user: UserDependency, id: IdDependency) -> Chat:
        return rag._get_chat(user=user, id=id)

    ChatDependency = Annotated[Chat, Depends(_get_chat, use_cache=False)]

    @app.get("/chat/{id}")
    @process_ragna_exception
    async def get_chat(chat: ChatDependency) -> ChatModel:
        return ChatModel.from_chat(chat)

    @app.post("/chat/{id}/start")
    @process_ragna_exception
    async def start_chat(chat: ChatDependency) -> ChatModel:
        return ChatModel.from_chat(await chat.start())

    @app.post("/chat/{id}/close")
    @process_ragna_exception
    async def close_chat(chat: ChatDependency) -> ChatModel:
        return ChatModel.from_chat(await chat.close())

    @app.post("/chat/{id}/answer")
    @process_ragna_exception
    async def answer(chat: ChatDependency, prompt: str) -> AnswerOutputModel:
        return AnswerOutputModel(
            message=MessageModel.from_message(await chat.answer(prompt)),
            chat=ChatModel.from_chat(chat),
        )

    return app
