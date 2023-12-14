import contextlib
import itertools
import uuid
from typing import Annotated, Any, AsyncIterator, Iterator, Type, cast

import aiofiles
import sse_starlette
from fastapi import Body, Depends, FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import ragna
import ragna.core
from ragna._utils import handle_localhost_origins
from ragna.core import Component, Rag, RagnaException
from ragna.core._rag import SpecialChatParams
from ragna.deploy import Config

from . import database, schemas


def app(config: Config) -> FastAPI:
    ragna.local_root(config.local_cache_root)

    rag = Rag()  # type: ignore[var-annotated]
    components_map: dict[str, Component] = {
        component.display_name(): rag._load_component(component)
        for component in itertools.chain(
            config.components.source_storages, config.components.assistants
        )
    }

    def get_component(display_name: str) -> Component:
        component = components_map.get(display_name)
        if component is None:
            raise RagnaException("Unknown component", display_name=display_name)

        return component

    app = FastAPI(title="ragna", version=ragna.__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=handle_localhost_origins(config.api.origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RagnaException)
    async def ragna_exception_handler(
        request: Request, exc: RagnaException
    ) -> JSONResponse:
        if exc.http_detail is RagnaException.EVENT:
            detail = exc.event
        elif exc.http_detail is RagnaException.MESSAGE:
            detail = str(exc)
        else:
            detail = cast(str, exc.http_detail)
        return JSONResponse(
            status_code=exc.http_status_code,
            content={"error": {"message": detail}},
        )

    @app.get("/")
    async def version() -> str:
        return ragna.__version__

    authentication = config.authentication()

    @app.post("/token")
    async def create_token(request: Request) -> str:
        return await authentication.create_token(request)

    UserDependency = Annotated[str, Depends(authentication.get_user)]

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

    @app.get("/components")
    async def get_components(_: UserDependency) -> schemas.Components:
        return schemas.Components(
            documents=sorted(config.document.supported_suffixes()),
            source_storages=[
                _get_component_json_schema(source_storage)
                for source_storage in config.components.source_storages
            ],
            assistants=[
                _get_component_json_schema(assistant)
                for assistant in config.components.assistants
            ],
        )

    database_url = config.api.database_url
    if database_url == "memory":
        database_url = "sqlite://"
    make_session = database.get_sessionmaker(database_url)

    @contextlib.contextmanager
    def get_session() -> Iterator[database.Session]:
        with make_session() as session:  # type: ignore[attr-defined]
            yield session

    @app.post("/document")
    async def create_document_upload_info(
        user: UserDependency,
        name: Annotated[str, Body(..., embed=True)],
    ) -> schemas.DocumentUpload:
        with get_session() as session:
            document = schemas.Document(name=name)
            metadata, parameters = await config.document.get_upload_info(
                config=config, user=user, id=document.id, name=document.name
            )
            database.add_document(
                session, user=user, document=document, metadata=metadata
            )
            return schemas.DocumentUpload(parameters=parameters, document=document)

    @app.put("/document")
    async def upload_document(
        token: Annotated[str, Form()], file: UploadFile
    ) -> schemas.Document:
        if not issubclass(config.document, ragna.core.LocalDocument):
            raise HTTPException(
                status_code=400,
                detail="Ragna configuration does not support local upload",
            )
        with get_session() as session:
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
        session: database.Session, *, user: str, chat: schemas.Chat
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

    @app.post("/chats")
    async def create_chat(
        user: UserDependency,
        chat_metadata: schemas.ChatMetadata,
    ) -> schemas.Chat:
        with get_session() as session:
            chat = schemas.Chat(metadata=chat_metadata)

            # Although we don't need the actual ragna.core.Chat object here,
            # we use it to validate the documents and metadata.
            schema_to_core_chat(session, user=user, chat=chat)

            database.add_chat(session, user=user, chat=chat)
            return chat

    @app.get("/chats")
    async def get_chats(user: UserDependency) -> list[schemas.Chat]:
        with get_session() as session:
            return database.get_chats(session, user=user)

    @app.get("/chats/{id}")
    async def get_chat(user: UserDependency, id: uuid.UUID) -> schemas.Chat:
        with get_session() as session:
            return database.get_chat(session, user=user, id=id)

    @app.post("/chats/{id}/prepare")
    async def prepare_chat(user: UserDependency, id: uuid.UUID) -> schemas.Message:
        with get_session() as session:
            chat = database.get_chat(session, user=user, id=id)

            core_chat = schema_to_core_chat(session, user=user, chat=chat)

            welcome = schemas.Message.from_core(await core_chat.prepare())

            chat.prepared = True
            chat.messages.append(welcome)
            database.update_chat(session, user=user, chat=chat)

            return welcome

    @app.post("/chats/{id}/answer")
    async def answer(
        user: UserDependency,
        id: uuid.UUID,
        prompt: Annotated[str, Body(..., embed=True)],
        stream: Annotated[bool, Body(..., embed=True)] = False,
    ) -> schemas.Message:
        with get_session() as session:
            chat = database.get_chat(session, user=user, id=id)
            chat.messages.append(
                schemas.Message(content=prompt, role=ragna.core.MessageRole.USER)
            )
            core_chat = schema_to_core_chat(session, user=user, chat=chat)

        core_answer = await core_chat.answer(prompt, stream=True)

        if stream:
            message_chunk = schemas.Message(
                content="",
                role=core_answer.role,
                sources=[
                    schemas.Source.from_core(source) for source in core_answer.sources
                ],
            )

            async def message_chunks() -> AsyncIterator[sse_starlette.ServerSentEvent]:
                chunks = []
                async for chunk in core_answer:
                    chunks.append(chunk)
                    message_chunk.content = chunk
                    yield sse_starlette.ServerSentEvent(message_chunk.model_dump_json())

                with get_session() as session:
                    answer = message_chunk
                    answer.content = "".join(chunks)
                    chat.messages.append(answer)
                    database.update_chat(session, user=user, chat=chat)

            return sse_starlette.EventSourceResponse(  # type: ignore[return-value]
                message_chunks()
            )
        else:
            answer = schemas.Message.from_core(await core_chat.answer(prompt))

            with get_session() as session:
                chat.messages.append(answer)
                database.update_chat(session, user=user, chat=chat)

            return answer

    @app.delete("/chats/{id}")
    async def delete_chat(user: UserDependency, id: uuid.UUID) -> None:
        with get_session() as session:
            database.delete_chat(session, user=user, id=id)

    return app
