"""
# Adding Components

While Ragna has builtin support for a few [assistants][ragna.assistants] and 
[source storages][ragna.source_storages], its real strength is allowing users
to incorporate custom components. This tutorial covers the basics of how to do that. 
"""


# %%
# ## Source Storage

# %%
# A [`Source`][ragna.core.Source] is a data class that stores the documents that Ragna will
# use to augment your prompts. [`SourceStorage`][ragna.core.SourceStorage]s, usually [vector
# databases][ragna.source_storages], are the tools Ragna uses to store the documents held in the
# [`Source`][ragna.core.Source]s.

# %%
# [`SourceStorage`][ragna.core.SourceStorage] has two abstract methods,
# [`store()`][ragna.core.SourceStorage.store] and [`retrieve()`][ragna.core.SourceStorage.retrieve].

# %%
# [`store()`][ragna.core.SourceStorage.store] takes a list of [`Source`][ragna.core.Source]s
# as an argument and places them in the database that you are using to hold them. This is
# different for each different source storage implementation.

# %%
# [`retrieve()`][ragna.core.SourceStorage.retrieve] returns sources matching
# the given prompt in order of relevance.

import uuid

from ragna.core import Document, Source, SourceStorage

import textwrap


class TutorialSourceStorage(SourceStorage):
    def __init__(self):
        # set up database
        self._storage: dict[int, list[Source]] = {}

    def store(self, documents: list[Document], chat_id: uuid.UUID) -> None:
        self._storage[chat_id] = [
            Source(
                id=str(uuid.uuid4()),
                document=document,
                location=f"page {page.number}"
                if (page := next(document.extract_pages())).number
                else "",
                content=(content := textwrap.shorten(page.text, width=100)),
                num_tokens=len(content.split()),
            )
            for document in documents
        ]

    def retrieve(
        self, documents: list[Document], prompt: str, *, chat_id: uuid.UUID
    ) -> list[Source]:
        return self._storage[chat_id]


# %%
# ## Assistant

# %%
# This is an example of an [`Assistant`][ragna.core.Assistant], which provides an interface between the user and the API for the LLM that they are using. For simplicity, we are not going to implement an actual LLM here, but rather a demo assistant that just mirrors back the inputs. This is similar to the [`RagnaDemoAssistant`][ragna.assistants.RagnaDemoAssistant].

# %%
# The main thing to do is to implement the [`answer()`][ragna.core.Assistant.answer] abstract method.
# The [`answer()`][ragna.core.Assistant.answer] method is where you put the logic to access your LLM.
# This could call an API directly or call a local LLM.

# %%
# Your [`answer()`][ragna.core.Assistant.answer] method should take a prompt in the form of a
# string, and a list of [`Source`][ragna.core.Source]s, in addition to whatever other arguments
# necessary for your particular assistant. The return type is an [`Iterator`](https://docs.python.org/3/library/stdtypes.html#typeiter) of strings.

# %%
# !!! note
#     Ragna also supports streaming responses from the assistant. See the
#     [example how to use streaming responses](../../generated/examples/gallery_streaming.md)
#     for more information.

from typing import Iterator

from ragna.core import Assistant, Source


class TutorialAssistant(Assistant):
    def answer(self, prompt: str, sources: list[Source]) -> Iterator[str]:
        yield (
            f"This is a default answer. There were {len(sources)} sources."
            f"The prompt was: "
            f"{prompt}"
        )


# %%
# ## Including Custom Python Objects

# %%
# If the module containing the custom object you want to include is in your
# [`PYTHONPATH`](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONPATH),
# you can either use the [config file](../../references/config.md#referencing-python-objects)
# to add it, or follow the [Python API](#using-the-python-api-with-custom-objects) instructions below.

# %%
# If the module containing the custom object you want to include is not in your
# [`PYTHONPATH`](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONPATH),
# suppose it is located at the path `~/tutorials/tutorial.py`. You can add `~/tutorial/` to your
# [`PYTHONPATH`](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONPATH) using
# the command
#
# ```bash
# $ export PYTHONPATH=$PYTHONPATH:~/tutorials/
# ```

# %%
# ## Using the Python API with Custom Objects

# We first import some helpers that tell Python where to find our demo document that we will
# use for RAG

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd().parent))

import documentation_helpers

document_path = documentation_helpers.assets / "ragna.txt"

with open(document_path) as file:
    print(file.read())

# %%
# We next import the [ragna.Rag][] class and set up a chat using the custom objects from above

from ragna import Rag

chat = Rag().chat(
    documents=[document_path],
    source_storage=TutorialSourceStorage,
    assistant=TutorialAssistant,
)

# %%
# Before we can ask a question, we need to [`prepare`][ragna.core.Chat.prepare] the chat, which
# under the hood stores the documents we have selected in the source storage.

_ = await chat.prepare()

# %%
# Finally, we can get an [`answer`][ragna.core.Chat.answer] to a question.

print(await chat.answer("What is Ragna?"))

# %%
# ## Using the Web UI

# %%
# To include our custom objects in the Web UI, make sure they are in your
# [`PYTHONPATH`](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONPATH),
# and list them in your [configuration file](../../references/config.md).

# %%
# Here is an example configuration file in the case that you would like to use one:

# %%
# ```toml
# local_root = "/home/ragnauser/.cache/ragna"
# authentication = "ragna.deploy.RagnaDemoAuthentication"
# document = "ragna.core.LocalDocument"
# source_storages = [
#     "tutorial.TutorialSourceStorage"
# ]
# assistants = [
#     "tutorial.TutorialAssistant"
# ]
#
# [api]
# hostname = "127.0.0.1"
# port = 31476
# root_path = ""
# url = "http://127.0.0.1:31476"
# database_url = "sqlite:////home/ragnauser/.cache/ragna/ragna.db"
# origins = [
#     "http://127.0.0.1:31477",
# ]
#
# [ui]
# hostname = "127.0.0.1"
# port = 31477
# origins = [
#     "http://127.0.0.1:31477",
# ]
# ```

# %%
# Note how the `tutorial.TutorialSourceStorage` and `tutorial.TutorialAssistant` classes are listed
# in the `source_storages` and `assistants` fields, respectively.
