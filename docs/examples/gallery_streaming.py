"""
# Streaming messages

Ragna supports streaming responses from the assistant. This example showcases how this
is performed using the Python and REST API.
"""

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
#       - [ragna.assistants.ClaudeOpus][]
#       - [ragna.assistants.ClaudeSonnet][]
#       - [ragna.assistants.ClaudeHaiku][]
#     - [Cohere](https://cohere.com/)
#       - [ragna.assistants.Command][]
#       - [ragna.assistants.CommandLight][]
#     - [Google](https://ai.google.dev/)
#       - [ragna.assistants.GeminiPro][]
#       - [ragna.assistants.GeminiUltra][]
#     - [OpenAI](https://openai.com/)
#       - [ragna.assistants.Gpt35Turbo16k][]
#       - [ragna.assistants.Gpt4][]
#     - [llamafile](https://github.com/Mozilla-Ocho/llamafile)
#       - [ragna.assistants.LlamafileAssistant][]
#     - [Ollama](https://ollama.com/)
#       - [ragna.assistants.OllamaGemma2B][]
#       - [ragna.assistants.OllamaLlama2][]
#       - [ragna.assistants.OllamaLlava][]
#       - [ragna.assistants.OllamaMistral][]
#       - [ragna.assistants.OllamaMixtral][]
#       - [ragna.assistants.OllamaOrcaMini][]
#       - [ragna.assistants.OllamaPhi2][]

from ragna import assistants


class DemoStreamingAssistant(assistants.RagnaDemoAssistant):
    def answer(self, messages):
        content = next(super().answer(messages))
        for chunk in content.split(" "):
            yield f"{chunk} "


# %%
# ## Python API
#
# Let's create and prepare a chat using the assistant we have defined above.

from pathlib import Path

import ragna._docs as ragna_docs

from ragna import Rag, source_storages

print(ragna_docs.SAMPLE_CONTENT)

document_path = Path.cwd() / "ragna.txt"

with open(document_path, "w") as file:
    file.write(ragna_docs.SAMPLE_CONTENT)

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

rest_api = ragna_docs.RestApi()

client, document = rest_api.start(config, authenticate=True, upload_document=True)

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
# Streaming the response is performed with [JSONL](https://jsonlines.org/). Each line
# in the response is valid JSON and corresponds to one chunk.

import json


with client.stream(
    "POST",
    f"/chats/{chat['id']}/answer",
    json={"prompt": "What is Ragna?", "stream": True},
) as response:
    chunks = [json.loads(data) for data in response.iter_lines()]

# %%
# The first chunk contains the full message object including the sources along the first
# chunk of the content.

print(len(chunks))
print(json.dumps(chunks[0], indent=2))

# %%
# Subsequent chunks no longer contain the sources.

print(json.dumps(chunks[1], indent=2))

# %%
# Joining the content of the chunks together results in the full message.

print("".join(chunk["content"] for chunk in chunks))

# %%
# Before we close the example, let's stop the REST API and have a look at what would
# have printed in the terminal if we had started it with the `ragna api` command.

rest_api.stop()
