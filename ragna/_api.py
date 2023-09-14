import uuid

from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI

from pydantic import BaseModel, Field, HttpUrl, Json

from ragna.core import Chat, MessageRole, Rag


class DocumentModel(BaseModel):
    id: UUID
    name: str

    @classmethod
    def _from_document(cls, document):
        return cls(
            id=UUID(document.id),
            name=document.name,
        )


class DocumentUploadInfoModel(BaseModel):
    url: HttpUrl
    data: dict[str, Any]
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
    documents: list[UUID]
    source_storage: str
    llm: str
    params: Json[dict] = Field(default_factory=dict)

    @classmethod
    def _from_chat(cls, chat):
        return cls(
            name=chat.name,
            documents=[d.id for d in chat.documents],
            source_storage=str(chat.source_storage),
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


# Can we make this a custom type for the DB? Maybe just subclass from str?
class RagnaId:
    @staticmethod
    def make():
        return RagnaId.from_uuid(uuid.uuid4())

    @staticmethod
    def is_valid(obj: Any) -> bool:
        if not isinstance(obj, str):
            return False

    @staticmethod
    def from_uuid(uuid: UUID) -> str:
        return str(uuid)


def api(**kwargs):
    rag = Rag(**kwargs)

    app = FastAPI()

    async def _authorize_user(user: str) -> str:
        # FIXME: implement auth here
        return user

    UserDependency = Annotated[str, Depends(_authorize_user)]

    @app.get("/document/new")
    def get_document_upload_info(
        user: UserDependency, name: str
    ) -> DocumentUploadInfoModel:
        return DocumentUploadInfoModel(
            url="https://foo.org",
            data={},
            document=DocumentModel(id=RagnaId.make(), name=name),
        )

    @app.post("/document/upload")
    def upload_document(user: UserDependency) -> DocumentModel:
        pass

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
                documents=[str(d) for d in chat_metadata.documents],
                source_storage=chat_metadata.source_storage,
                llm=chat_metadata.llm,
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
