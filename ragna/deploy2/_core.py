import contextlib

from . import _database as database
from . import schemas

# UserDependency = Annotated[str, Depends(authentication.get_user)]


# def _get_component_json_schema(
#     component: Type[Component],
# ) -> dict[str, dict[str, Any]]:
#     json_schema = component._protocol_model().model_json_schema()
#     # FIXME: there is likely a better way to exclude certain fields builtin in
#     #  pydantic
#     for special_param in SpecialChatParams.model_fields:
#         if "properties" in json_schema and special_param in json_schema["properties"]:
#             del json_schema["properties"][special_param]
#         if "required" in json_schema and special_param in json_schema["required"]:
#             json_schema["required"].remove(special_param)
#     return json_schema
#
#
# async def get_components(_: UserDependency) -> schemas.Components:
#     return schemas.Components(
#         documents=sorted(config.document.supported_suffixes()),
#         source_storages=[
#             _get_component_json_schema(source_storage)
#             for source_storage in config.components.source_storages
#         ],
#         assistants=[
#             _get_component_json_schema(assistant)
#             for assistant in config.components.assistants
#         ],
#     )


database_url = config.api.database_url
if database_url == "memory":
    database_url = "sqlite://"
make_session = database.get_sessionmaker(database_url)


@contextlib.contextmanager
def get_session() -> Iterator[database.Session]:
    with make_session() as session:  # type: ignore[attr-defined]
        yield session


async def create_document_upload_info(
    user: UserDependency,
    name: Annotated[str, Body(..., embed=True)],
) -> schemas.DocumentUpload:
    with get_session() as session:
        document = schemas.Document(name=name)
        metadata, parameters = await config.document.get_upload_info(
            config=config, user=user, id=document.id, name=document.name
        )
        database.add_document(session, user=user, document=document, metadata=metadata)
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


async def get_chats(user: UserDependency) -> list[schemas.Chat]:
    with get_session() as session:
        return database.get_chats(session, user=user)


async def get_chat(user: UserDependency, id: uuid.UUID) -> schemas.Chat:
    with get_session() as session:
        return database.get_chat(session, user=user, id=id)


async def prepare_chat(user: UserDependency, id: uuid.UUID) -> schemas.Message:
    with get_session() as session:
        chat = database.get_chat(session, user=user, id=id)

        core_chat = schema_to_core_chat(session, user=user, chat=chat)

        welcome = schemas.Message.from_core(await core_chat.prepare())

        chat.prepared = True
        chat.messages.append(welcome)
        database.update_chat(session, user=user, chat=chat)

        return welcome


async def answer(
    user: UserDependency, chat_id: uuid.UUID, prompt: str
) -> schemas.Message:
    with get_session() as session:
        chat = database.get_chat(session, user=user, id=id)
        chat.messages.append(
            schemas.Message(content=prompt, role=ragna.core.MessageRole.USER)
        )

        core_chat = schema_to_core_chat(session, user=user, chat=chat)

        answer = schemas.Message.from_core(await core_chat.answer(prompt))

        chat.messages.append(answer)
        database.update_chat(session, user=user, chat=chat)

        return answer


async def delete_chat(user: UserDependency, id: uuid.UUID) -> None:
    with get_session() as session:
        database.delete_chat(session, user=user, id=id)
