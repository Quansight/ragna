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

from ragna.core import Document, Source, SourceStorage


class TutorialSourceStorage(SourceStorage):
    def __init__(self):
        # set up database
        self._storage: dict[int, list[Source]] = {}

    def store(self, documents: list[Document], chat_id: int) -> None:
        self._storage[chat_id] = [Source(document=document) for document in documents]

    def retrieve(
        self, documents: list[Document], prompt: str, *, chat_id: int
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
            f"The prompt was:"
            f"{prompt}"
        )


# %%
# ## Including Custom Python Objects

# %%
# If the module containing the custom object you want to include is in your
# [`PYTHONPATH`](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONPATH),
# you can use the [config file](../../../references/config/#referencing-python-objects)
# to add it.

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
# Once the module(s) containing your objects is(are) in your
# [`PYTHONPATH`](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONPATH), you can
# you can include it(them) in Ragna using the
# [config file](../../../references/config/#referencing-python-objects).
