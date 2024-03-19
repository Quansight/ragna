"""
# Adding Components

Ragna has builtin support for several [assistants][ragna.assistants] and 
[source storages][ragna.source_storages], but there may be cases where you 
want to use one that is not currently supported.

This tutorial walks you through the basics of adding components
that are not currently officially supported. 
"""

# %%
# ## Adding an LLM Assistant

# %%
# The main thing to do is to implement the [`answer()`][ragna.core.Assistant.answer] abstract method.
# The [`answer()`][ragna.core.Assistant.answer] method is where you put the logic to access your LLM.
# This could call an API directly, call other member functions of your assistant that call an API,
# or call a local LLM. Ragna is designed to give you that flexibility.

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
            ""
            f"The prompt was"
            f"{prompt}"
        )


# %%
# ## Adding a Source Storage

from ragna.core import Document, Source, SourceStorage


class TutorialSourceStorage(SourceStorage):
    def __init__(self):
        # import database api here

        # set up database
        self._storage: dict[int, list[Source]] = {}

    def store(self, documents: list[Document], chat_id: int) -> None:
        self._storage[chat_id] = [
            Source(
                document=document,
            )
            for document in documents
        ]

    def retrieve(
        self, documents: list[Document], prompt: str, *, chat_id: int
    ) -> list[Source]:
        return self._storage[chat_id]


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

# %%
# ## Including External Python Objects

# %%
# If the module containing external object you want to include is not in your
# [`PYTHONPATH`](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONPATH),
# suppose it is located at the path `~/tutorials/tutorial.py`. You can add `~/tutorial/` to your
# [`PYTHONPATH`](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONPATH) using
# the command
# ```bash
# $ export PYTHONPATH=$PYTHONPATH:~/tutorials/
# ```

# %%
# If the external object is already in your
# [`PYTHONPATH`](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONPATH), e.g.
# already in your virtual environment, then the above `#!bash export` command is not necessary.

# %%
# Once the module(s) containing your objects is(are) in your
# [`PYTHONPATH`](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONPATH), you can
# you can include them in Ragna by setting their corresponding
# [environment variables](../../references/config.md#environment-variables):

# %%
# ```bash
# $ export RAGNA_ASSISTANTS='["tutorial.TutorialAssistant"]'
# ```

# %%
# for importing the [`TutorialAssistant`](../../generated/tutorials/gallery_adding_components.md#adding-an-llm-assistant) from above, and

# %%
# ```bash
# $ export RAGNA_SOURCE_STORAGES='["tutorial.TutorialSourceStorage"]'
# ```

# %%
# for importing the [`TutorialSourceStorage`](../../generated/tutorials/gallery_adding_components.md#adding-a-source-storage) from above.
