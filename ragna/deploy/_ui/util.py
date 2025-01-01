import uuid
from datetime import datetime

import panel as pn
from emoji import emojize


# This and `improve_message` were copied from the old [`ApiWrapper`](https://github.com/Quansight/ragna/issues/521).
# The interface they provide is open for discussion
async def get_improved_chats(engine):
    json_data = [
        chat.model_dump(mode="json") for chat in engine.get_chats(user=pn.state.user)
    ]
    for chat in json_data:
        chat["messages"] = [improve_message(msg) for msg in chat["messages"]]
    return json_data


def improve_message(msg):
    msg["timestamp"] = datetime.strptime(msg["timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ")
    msg["content"] = emojize(msg["content"], language="alias")
    return msg


async def answer_improved(engine, chat_id, prompt):
    async for message in engine.answer_stream(
        user=pn.state.user, chat_id=uuid.UUID(chat_id), prompt=prompt
    ):
        yield improve_message(message.model_dump(mode="json"))
