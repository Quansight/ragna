"""
# Custom Components

While Ragna has builtin support for a few [source storages][ragna.source_storages]
and [assistants][ragna.assistants], its real strength lies in allowing users
to incorporate custom components. This tutorial covers how to do that.
"""

# %%
# ## Components
#
# ### Source Storage
#
# [ragna.core.SourceStorage][]s are objects that take a number of documents and
# [ragna.core.SourceStorage.store][] their content in way such that relevant parts for a
# given user prompt can be [ragna.core.SourceStorage.retrieve][]d in the form of
# [ragna.core.Source][]s. Usually, source storages are vector databases.
#
# In this tutorial, we define a minimal `TutorialSourceStorage` that is similar to
# [ragna.source_storages.RagnaDemoSourceStorage][]. In `.store()` we create the
# `Source`s with the first 100 characters of each document and store them in memory
# based on the unique `chat_id`. In `retrieve()` we return all the stored sources
# for the chat and regardless of the user `prompt`.
#
# !!! note
#
#     The `chat_id` used in both methods will not be passed by default, but rather has
#     to be requested explicitly. How this works in detail will be explained later in
#     this tutorial in the [Custom Parameters](#custom-parameters) section.

import uuid

from ragna.core import Document, Source, SourceStorage, Message


class TutorialSourceStorage(SourceStorage):
    def __init__(self):
        self._storage: dict[uuid.UUID, list[Source]] = {}

    def store(self, documents: list[Document], *, chat_id: uuid.UUID) -> None:
        print(f"Running {type(self).__name__}().store()")

        self._storage[chat_id] = [
            Source(
                id=str(uuid.uuid4()),
                document=document,
                location="N/A",
                content=(content := next(document.extract_pages()).text[:100]),
                num_tokens=len(content.split()),
            )
            for document in documents
        ]

    def retrieve(
        self, documents: list[Document], prompt: str, *, chat_id: uuid.UUID
    ) -> list[Source]:
        print(f"Running {type(self).__name__}().retrieve()")
        return self._storage[chat_id]


# %%
# ### Assistant
#
# [ragna.core.Assistant][]s are objects that take the chat history as list of
# [ragna.core.Message][]s and their relevant [ragna.core.Source][]s and generate a
# response from that. Usually, assistants are LLMs.
#
# In this tutorial, we define a minimal `TutorialAssistant` that is similar to
# [ragna.assistants.RagnaDemoAssistant][]. In `.answer()` we mirror back the user
# prompt and also the number of sources we were given.
#
# !!! note
#
#     The answer needs to be `yield`ed instead of `return`ed. By yielding multiple
#     times, the answer can be streamed back. See the
#     [streaming example](../../generated/examples/gallery_streaming.md) for more
#     information.

from typing import Iterator

from ragna.core import Assistant, Source


class TutorialAssistant(Assistant):
    def answer(self, messages: list[Message]) -> Iterator[str]:
        print(f"Running {type(self).__name__}().answer()")
        # For simplicity, we only deal with the last message here, i.e. the latest user
        # prompt.
        prompt, sources = (message := messages[-1]).content, message.sources
        yield (
            f"To answer the user prompt '{prompt}', "
            f"I was given {len(sources)} source(s)."
        )


# %%
# ## Usage
#
# Now that we have defined a custom [ragna.core.SourceStorage][] and
# [ragna.core.Assistant][], let's have a look on how to use them with Ragna. Let's start
# with the Python API.
#
# ### Python API
#
# We first create a sample document.

from pathlib import Path

import ragna._docs as ragna_docs

print(ragna_docs.SAMPLE_CONTENT)

document_path = Path.cwd() / "ragna.txt"

with open(document_path, "w") as file:
    file.write(ragna_docs.SAMPLE_CONTENT)

# %%
# Next, we create a new [ragna.core.Chat][] with our custom components.

from ragna import Rag

chat = Rag().chat(
    documents=[document_path],
    source_storage=TutorialSourceStorage,
    assistant=TutorialAssistant,
)

# %%
# From here on, you can use your custom components exactly like the builtin ones. For
# more details, have a look at the
# [Python API tutorial](../../generated/tutorials/gallery_python_api.md).

_ = await chat.prepare()

# %%

answer = await chat.answer("What is Ragna?")

# %%

print(answer)

# %%
for idx, source in enumerate(answer.sources, 1):
    print(f"{idx}. {source.content}")

# %%
# ### REST API
#
# To use custom components in Ragna's REST API, we need to include the components in
# the corresponding arrays in the configuration file. If you don't have a `ragna.toml`
# configuration file yet, see the [config reference](../../references/config.md) on how
# to create one.
#
# For example, if we put the `TutorialSourceStorage` and `TutorialAssistant` classes in
# a `tutorial.py` module, we can expand the `source_storages` and `assistants` arrays
# like this
#
# ```toml
# source_storages = [
#     ...
#     "tutorial.TutorialSourceStorage"
# ]
# assistants = [
#     ...
#     "tutorial.TutorialAssistant"
# ]
# ```
#
# !!! note
#
#     Make sure the `tutorial.py` module is on Python's search path. See the
#     [config reference](../../references/config.md#referencing-python-objects) for
#     details.
#
# With the configuration set up, we now start the REST API. For the purpose of this
# tutorial we replicate the same programmatically. For general information on how to use
# the REST API, have a look at the
# [REST API tutorial](../../generated/tutorials/gallery_rest_api.md).

from ragna.deploy import Config

config = Config(
    source_storages=[TutorialSourceStorage],
    assistants=[TutorialAssistant],
)

rest_api = ragna_docs.RestApi()

client, document = rest_api.start(config, authenticate=True, upload_document=True)

# %%
# To select our custom components, we pass their display names to the chat creation.
#
# !!! tip
#
#     By default [ragna.core.Component.display_name][] returns the name of the class,
#     but can be overridden, e.g. to format the name better.

import json

response = client.post(
    "/chats",
    json={
        "name": "Tutorial REST API",
        "documents": [document],
        "source_storage": TutorialSourceStorage.display_name(),
        "assistant": TutorialAssistant.display_name(),
        "params": {},
    },
).raise_for_status()
chat = response.json()

client.post(f"/chats/{chat['id']}/prepare").raise_for_status()

response = client.post(
    f"/chats/{chat['id']}/answer",
    json={"prompt": "What is Ragna?"},
).raise_for_status()
answer = response.json()
print(json.dumps(answer, indent=2))

# %%
# Let's stop the REST API and have a look at what would have printed in the terminal if
# we had started it with the `ragna api` command.

rest_api.stop()

# %%
# ### Web UI
#
# The setup for the web UI is exactly the same as for the [REST API](#rest-api). If you
# have your configuration set up, you can start the web UI and use the custom
# components. See the [web UI tutorial](../../generated/tutorials/gallery_rest_api.md)
# for details.
#
#
# ![Create-chat-modal of Ragna's web UI with the TutorialSourceStorage and TutorialAssistant as selected options](../../assets/images/ragna-tutorial-components.png)
#
# !!! warning
#
#     See the section about [custom parameters for the web UI](#web-ui_1) for some
#     limitations using custom components in the web UI.

# %%
# ## Custom parameters
#
# Ragna supports passing parameters to the components on a per-chat level. The extra
# parameters are defined by adding them to the signature of the method. For example,
# let's define a more elaborate assistant that accepts the following arguments:
#
# - `my_required_parameter` must be passed and has to be an `int`
# - `my_optional_parameter` may be passed and has to be a `str` if passed


class ElaborateTutorialAssistant(Assistant):
    def answer(
        self,
        messages: list[Message],
        *,
        my_required_parameter: int,
        my_optional_parameter: str = "foo",
    ) -> Iterator[str]:
        print(f"Running {type(self).__name__}().answer()")
        yield (
            f"I was given {my_required_parameter=} and {my_optional_parameter=}."
        )


# %%
# ### Python API
#
# To pass custom parameters to the components, pass them as keyword arguments when
# creating a chat.

chat = Rag().chat(
    documents=[document_path],
    source_storage=TutorialSourceStorage,
    assistant=ElaborateTutorialAssistant,
    my_required_parameter=3,
    my_optional_parameter="bar",
)

_ = await chat.prepare()
print(await chat.answer("Hello!"))

# %%
# The chat creation will fail if a required parameter is not passed or a wrong type is
# passed for any parameter.

try:
    Rag().chat(
        documents=[document_path],
        source_storage=TutorialSourceStorage,
        assistant=ElaborateTutorialAssistant,
    )
except Exception as exc:
    print(exc)

# %%

try:
    Rag().chat(
        documents=[document_path],
        source_storage=TutorialSourceStorage,
        assistant=ElaborateTutorialAssistant,
        my_required_parameter="bar",
        my_optional_parameter=3,
    )
except Exception as exc:
    print(exc)

# %%
# ### REST API

config = Config(
    source_storages=[TutorialSourceStorage],
    assistants=[ElaborateTutorialAssistant],
)

rest_api = ragna_docs.RestApi()

client, document = rest_api.start(config, authenticate=True, upload_document=True)

# %%
# To pass custom parameters, define them in the `params` mapping when creating a new
# chat.

response = client.post(
    "/chats",
    json={
        "name": "Tutorial REST API",
        "documents": [document],
        "source_storage": TutorialSourceStorage.display_name(),
        "assistant": ElaborateTutorialAssistant.display_name(),
        "params": {
            "my_required_parameter": 3,
            "my_optional_parameter": "bar",
        },
    },
).raise_for_status()
chat = response.json()

# %%

client.post(f"/chats/{chat['id']}/prepare").raise_for_status()

response = client.post(
    f"/chats/{chat['id']}/answer",
    json={"prompt": "What is Ragna?"},
).raise_for_status()
answer = response.json()
print(json.dumps(answer, indent=2))

# %%
# Let's stop the REST API and have a look at what would have printed in the terminal if
# we had started it with the `ragna api` command.

rest_api.stop()

# %%
# ### Web UI
#
# !!! warning
#     Unfortunately, Ragna's web UI currently does **not** support arbitrary custom
#     parameters. This is actively worked on and progress is tracked in
#     [#217](https://github.com/Quansight/ragna/issues/217). Until this is resolved,
#     the source storage and the assistant together take the following four
#     parameters:
#
#     1. `chunk_size: int`
#     2. `chunk_overlap: int`
#     3. `num_tokens: int`
#     4. `max_new_tokens: int`
#
#     When using Ragna's builtin components, all source storages cover parameters 1. to
#     3. and all assistant cover parameter 4.

# %%
# ## Sync or `async`?
#
# So far we have `def`ined all of the abstract methods of the components as regular,
# i.e. synchronous methods. However, this is *not* a requirement. If you want to run
# `async` code inside the methods, define them with `async def` and Ragna will
# handle the rest for you. Internally, Ragna runs synchronous methods on a thread to
# avoid blocking the main thread. Asynchronous methods are scheduled on the main event
# loop.
#
# Let's have a look at a minimal example.

import asyncio
import time
from typing import AsyncIterator


class AsyncAssistant(Assistant):
    async def answer(self, messages: list[Message]) -> AsyncIterator[str]:
        print(f"Running {type(self).__name__}().answer()")
        start = time.perf_counter()
        await asyncio.sleep(0.3)
        stop = time.perf_counter()
        yield f"I've waited for {stop - start} seconds!"


chat = Rag().chat(
    documents=[document_path],
    source_storage=TutorialSourceStorage,
    assistant=AsyncAssistant,
)

_ = await chat.prepare()
print(await chat.answer("Hello!"))
