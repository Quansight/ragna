import uuid
from typing import Annotated, Any, AsyncIterator, Type, cast

import aiofiles
from fastapi import (
    APIRouter,
    Body,
    Depends,
    FastAPI,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import ragna
import ragna.core
from ragna._compat import aiter, anext
from ragna.core import Assistant, Component, Rag, RagnaException, SourceStorage
from ragna.core._rag import SpecialChatParams
from ragna.deploy import Config

from . import schemas
from ._session import UserDependency as _UserDependency


def make_router(
    config: Config, database, ignore_unavailable_components: bool
) -> FastAPI:
    router = APIRouter(tags=["api"])

    rag = Rag()  # type: ignore[var-annotated]
    components_map: dict[str, Component] = {}
    for components in [config.source_storages, config.assistants]:
        components = cast(list[Type[Component]], components)
        at_least_one = False
        for component in components:
            loaded_component = rag._load_component(
                component, ignore_unavailable=ignore_unavailable_components
            )
            if loaded_component is None:
                print(
                    f"Ignoring {component.display_name()}, because it is not available."
                )
            else:
                at_least_one = True
                components_map[component.display_name()] = loaded_component

        if not at_least_one:
            raise RagnaException(
                "No component available",
                components=[component.display_name() for component in components],
            )

    def get_component(display_name: str) -> Component:
        component = components_map.get(display_name)
        if component is None:
            raise RagnaException(
                "Unknown component",
                display_name=display_name,
                http_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                http_detail=RagnaException.MESSAGE,
            )

        return component

    async def _get_username(user: _UserDependency):
        return user.username

    UserDependency = Annotated[str, Depends(_get_username)]

    def _get_component_json_schema(
        component: Type[Component],
    ) -> dict[str, dict[str, Any]]:
        json_schema = component._protocol_model().model_json_schema()
        # FIXME: there is likely a better way to exclude certain fields builtin in
        #  pydantic
        for special_param in SpecialChatParams.model_fields:
            if (
                "properties" in json_schema
                and special_param in json_schema["properties"]
            ):
                del json_schema["properties"][special_param]
            if "required" in json_schema and special_param in json_schema["required"]:
                json_schema["required"].remove(special_param)
        return json_schema

    @router.get("/components")
    async def get_components(_: UserDependency) -> schemas.Components:
        return schemas.Components(
            documents=sorted(config.document.supported_suffixes()),
            source_storages=[
                _get_component_json_schema(type(source_storage))
                for source_storage in components_map.values()
                if isinstance(source_storage, SourceStorage)
            ],
            assistants=[
                _get_component_json_schema(type(assistant))
                for assistant in components_map.values()
                if isinstance(assistant, Assistant)
            ],
        )

    @router.post("/document")
    async def create_document_upload_info(
        user: UserDependency,
        name: Annotated[str, Body(..., embed=True)],
    ) -> schemas.DocumentUpload:
        with database.session() as session:
            document = schemas.Document(name=name)
            metadata, parameters = await config.document.get_upload_info(
                config=config, user=user, id=document.id, name=document.name
            )
            database.add_document(
                session, user=user, document=document, metadata=metadata
            )
            return schemas.DocumentUpload(parameters=parameters, document=document)

    @router.put("/document")
    async def upload_document(
        token: Annotated[str, Form()], file: UploadFile
    ) -> schemas.Document:
        if not issubclass(config.document, ragna.core.LocalDocument):
            raise HTTPException(
                status_code=400,
                detail="Ragna configuration does not support local upload",
            )
        with database.session() as session:
            user, id = ragna.core.LocalDocument.decode_upload_token(token)
            document, metadata = database.get_document(session, user=user, id=id)

            core_document = ragna.core.LocalDocument(
                id=document.id, name=document.name, metadata=metadata
            )
            core_document.path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(core_document.path, "wb") as document_file:
                while content := await file.read(1024):
                    await document_file.write(content)

            return document

    def schema_to_core_chat(
        session, *, user: str, chat: schemas.Chat
    ) -> ragna.core.Chat:
        core_chat = rag.chat(
            documents=[
                config.document(
                    id=document.id,
                    name=document.name,
                    metadata=database.get_document(
                        session,
                        user=user,
                        id=document.id,
                    )[1],
                )
                for document in chat.metadata.documents
            ],
            source_storage=get_component(chat.metadata.source_storage),  # type: ignore[arg-type]
            assistant=get_component(chat.metadata.assistant),  # type: ignore[arg-type]
            user=user,
            chat_id=chat.id,
            chat_name=chat.metadata.name,
            **chat.metadata.params,
        )
        # FIXME: We need to reconstruct the previous messages here. Right now this is
        #  not needed, because the chat itself never accesses past messages. However,
        #  if we implement a chat history feature, i.e. passing past messages to
        #  the assistant, this becomes crucial.
        core_chat._messages = []
        core_chat._prepared = chat.prepared

        return core_chat

    @router.post("/chats")
    async def create_chat(
        user: UserDependency,
        chat_metadata: schemas.ChatMetadata,
    ) -> schemas.Chat:
        with database.session() as session:
            chat = schemas.Chat(metadata=chat_metadata)

            # Although we don't need the actual ragna.core.Chat object here,
            # we use it to validate the documents and metadata.
            schema_to_core_chat(session, user=user, chat=chat)

            database.add_chat(session, user=user, chat=chat)
            return chat

    @router.get("/chats")
    async def get_chats(user: UserDependency) -> list[schemas.Chat]:
        with database.session() as session:
            return database.get_chats(session, user=user)

    @router.get("/chats/{id}")
    async def get_chat(user: UserDependency, id: uuid.UUID) -> schemas.Chat:
        with database.session() as session:
            return database.get_chat(session, user=user, id=id)

    @router.post("/chats/{id}/prepare")
    async def prepare_chat(user: UserDependency, id: uuid.UUID) -> schemas.Message:
        with database.session() as session:
            chat = database.get_chat(session, user=user, id=id)

        core_chat = schema_to_core_chat(session, user=user, chat=chat)

        welcome = schemas.Message.from_core(await core_chat.prepare())

        with database.session() as session:
            chat.prepared = True
            chat.messages.append(welcome)
            database.update_chat(session, user=user, chat=chat)

        return welcome

    @router.post("/chats/{id}/answer")
    async def answer(
        user: UserDependency,
        id: uuid.UUID,
        prompt: Annotated[str, Body(..., embed=True)],
        stream: Annotated[bool, Body(..., embed=True)] = False,
    ) -> schemas.Message:
        with database.session() as session:
            chat = database.get_chat(session, user=user, id=id)
            chat.messages.append(
                schemas.Message(content=prompt, role=ragna.core.MessageRole.USER)
            )
            core_chat = schema_to_core_chat(session, user=user, chat=chat)

        core_answer = await core_chat.answer(prompt, stream=stream)

        if stream:

            async def message_chunks() -> AsyncIterator[BaseModel]:
                core_answer_stream = aiter(core_answer)
                content_chunk = await anext(core_answer_stream)

                answer = schemas.Message(
                    content=content_chunk,
                    role=core_answer.role,
                    sources=[
                        schemas.Source.from_core(source)
                        for source in core_answer.sources
                    ],
                )
                yield answer

                # Avoid sending the sources multiple times
                answer_chunk = answer.model_copy(update=dict(sources=None))
                content_chunks = [answer_chunk.content]
                async for content_chunk in core_answer_stream:
                    content_chunks.append(content_chunk)
                    answer_chunk.content = content_chunk
                    yield answer_chunk

                with database.session() as session:
                    answer.content = "".join(content_chunks)
                    chat.messages.append(answer)
                    database.update_chat(session, user=user, chat=chat)

            async def to_jsonl(models: AsyncIterator[Any]) -> AsyncIterator[str]:
                async for model in models:
                    yield f"{model.model_dump_json()}\n"

            return StreamingResponse(  # type: ignore[return-value]
                to_jsonl(message_chunks())
            )
        else:
            answer = schemas.Message.from_core(core_answer)

            with database.session() as session:
                chat.messages.append(answer)
                database.update_chat(session, user=user, chat=chat)

            return answer

    @router.delete("/chats/{id}")
    async def delete_chat(user: UserDependency, id: uuid.UUID) -> None:
        with database.session() as session:
            database.delete_chat(session, user=user, id=id)

    return router
