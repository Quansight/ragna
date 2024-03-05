"""
# Streaming messages

Ragna supports streaming responses from the assistant. This example showcases how this
is performed using the Python and REST API.
"""

# %%
# Before we start this example, we import some helpers.

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd().parent))

import documentation_helpers

# %%
# ## Setup streaming assistant
#
# To be able to stream a message from an assistant, it needs to support streaming. For
# this example, we subclass the [ragna.assistants.RagnaDemoAssistant][], split its
# message on whitespace, and return the individual chunks.
#
# !!! tip
#
#     Of the assistants that Ragna has built in, the following ones support streaming:
#
#     - [Anthropic](https://www.anthropic.com/)
#       - [ragna.assistants.Claude][]
#       - [ragna.assistants.ClaudeInstant][]
#     - [Cohere](https://cohere.com/)
#       - [ragna.assistants.Command][]
#       - [ragna.assistants.CommandLight][]
#     - [Google](https://ai.google.dev/)
#       - [ragna.assistants.GeminiPro][]
#       - [ragna.assistants.GeminiUltra][]
#     - [OpenAI](https://openai.com/)
#       - [ragna.assistants.Gpt35Turbo16k][]
#       - [ragna.assistants.Gpt4][]

from ragna import assistants


class DemoStreamingAssistant(assistants.RagnaDemoAssistant):
    @property
    def max_input_size(self) -> int:
        return 0

    def answer(self, prompt, sources):
        content = next(super().answer(prompt, sources))
        for chunk in content.split(" "):
            yield f"{chunk} "


# %%
# ## Python API
#
# Let's create and prepare a chat using the assistant we have defined above.

from ragna import Rag, source_storages

document_path = documentation_helpers.assets / "ragna.txt"

chat = Rag().chat(
    documents=[document_path],
    source_storage=source_storages.RagnaDemoSourceStorage,
    assistant=DemoStreamingAssistant,
)
_ = await chat.prepare()

# %%

message = await chat.answer("What is Ragna?", stream=True)

# %%
# At this stage, we cannot access the content of the message, e.g. by printing it.

try:
    print(message)
except Exception as error:
    print(f"{type(error).__name__}: {error}")

# %%
# To get the individual chunks, we asynchronously iterate over the `message`.

chunks = [chunk async for chunk in message]

print(len(chunks))
print(chunks)

# %%
# Joining the chunks together results in the full message.

print("".join(chunks))

# %%
# ## REST API

from ragna.deploy import Config

config = Config(assistants=[DemoStreamingAssistant])

rest_api = documentation_helpers.RestApi()

client = rest_api.start(config, authenticate=True)

# %%
# Upload the document.

document_upload = (
    client.post("/document", json={"name": document_path.name})
    .raise_for_status()
    .json()
)

document = document_upload["document"]

parameters = document_upload["parameters"]
client.request(
    parameters["method"],
    parameters["url"],
    data=parameters["data"],
    files={"file": open(document_path, "rb")},
).raise_for_status()

# %%
# Start and prepare the chat

chat = (
    client.post(
        "/chats",
        json={
            "name": "Tutorial REST API",
            "documents": [document],
            "source_storage": source_storages.RagnaDemoSourceStorage.display_name(),
            "assistant": DemoStreamingAssistant.display_name(),
            "params": {},
        },
    )
    .raise_for_status()
    .json()
)

client.post(f"/chats/{chat['id']}/prepare").raise_for_status()

# %%
# Streaming the response is performed with
# [server-sent events (SSE)](https://en.wikipedia.org/wiki/Server-sent_events).

import httpx_sse
import json

chunks = []
with httpx_sse.connect_sse(
    client,
    "POST",
    f"/chats/{chat['id']}/answer",
    json={"prompt": "What is Ragna?", "stream": True},
) as event_source:
    for sse in event_source.iter_sse():
        chunks.append(json.loads(sse.data))

# %%
# The first event contains the full message object including the sources along the first
# chunk of the content.

print(len(chunks))
print(json.dumps(chunks[0], indent=2))

# %%
# Subsequent events no longer contain the sources.

print(json.dumps(chunks[1], indent=2))

# %%
# Joining the chunks together results in the full message.

print("".join(chunk["content"] for chunk in chunks))

# %%
# Before we close the tutorial, let's stop the REST API and have a look at what would
# have printed in the terminal if we had started it the regular way.

rest_api.stop()
