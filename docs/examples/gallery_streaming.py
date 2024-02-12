"""
# Streaming messages

The [Python API](../../references/python-api.md) is the best place to get started with
Ragna and understand its key components. It's also the best way to continue
experimenting with components and configurations for your particular use case.

This tutorial walks you through basic steps of using Ragnas Python API.
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
#         - [ragna.assistants.Claude][]
#         - [ragna.assistants.ClaudeInstant][]
#     - [Google](https://ai.google.dev/)
#         - [ragna.assistants.GeminiPro][]
#         - [ragna.assistants.GeminiUltra][]
#     - [OpenAI](https://openai.com/)
#         - [ragna.assistants.Gpt35Turbo16k][]
#         - [ragna.assistants.Gpt4][]

from ragna import assistants


class RagnaDemoStreamingAssistant(assistants.RagnaDemoAssistant):
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

chat = Rag().chat(
    documents=[documentation_helpers.assets / "ragna.txt"],
    source_storage=source_storages.RagnaDemoSourceStorage,
    assistant=RagnaDemoStreamingAssistant,
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

config = Config(components={"assistants": [RagnaDemoStreamingAssistant]})

rest_api = documentation_helpers.RestApi()

client = rest_api.start(config, authenticate=True)
