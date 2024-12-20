import uuid
from datetime import datetime

import emoji
import panel as pn
import param

from ragna.deploy import _schemas as schemas
from ragna.deploy._engine import Engine


class ApiWrapper(param.Parameterized):
    def __init__(self, engine: Engine):
        super().__init__()
        self._user = pn.state.user
        self._engine = engine

    async def get_corpus_names(self):
        return await self._engine.get_corpuses()

    async def get_corpus_metadata(self):
        return await self._engine.get_corpus_metadata()

    async def get_chats(self):
        json_data = [
            chat.model_dump(mode="json")
            for chat in self._engine.get_chats(user=self._user)
        ]
        for chat in json_data:
            chat["messages"] = [self.improve_message(msg) for msg in chat["messages"]]
        return json_data

    async def answer(self, chat_id, prompt):
        async for message in self._engine.answer_stream(
            user=self._user, chat_id=uuid.UUID(chat_id), prompt=prompt
        ):
            yield self.improve_message(message.model_dump(mode="json"))

    def get_components(self):
        return self._engine.get_components()

    async def start_and_prepare(
        self, name, input, corpus_name, source_storage, assistant, params
    ):
        chat = self._engine.create_chat(
            user=self._user,
            chat_creation=schemas.ChatCreation(
                name=name,
                input=input,
                source_storage=source_storage,
                assistant=assistant,
                corpus_name=corpus_name,
                params=params,
            ),
        )
        await self._engine.prepare_chat(user=self._user, id=chat.id)
        return str(chat.id)

    def improve_message(self, msg):
        msg["timestamp"] = datetime.strptime(msg["timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ")
        msg["content"] = emoji.emojize(msg["content"], language="alias")
        return msg
