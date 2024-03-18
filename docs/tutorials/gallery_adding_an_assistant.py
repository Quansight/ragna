"""
# Adding an Assistant

Ragna has builtin support for [several assistants][ragna.assistants], but there may be cases where you 
want to use one that is not currently supported.

This tutorial walks you through the basics of creating an assistant for LLMs that are not
currently supported. 
"""

# %%
# ## The Finished Product

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
# ## The Explanation

# %%
# ### Step 0: Import Necessary Modules

# %%
# First start by importing some necessary components.

# %%
# Your assistant will subclass the [`Assistant`][ragna.core.Assistant] abstract base class and
# [`Source`][ragna.core.Source] will be used to hold the documents or files sent to the LLM.

# %%
# ```python
# from typing import Iterator
#
# from ragna.core import Assistant, Source
# ```

# %%
# ### Step 1: Write the Assistant

# %%
# The main thing to do is to implement the `answer` abstract method. The
# [`answer`][ragna.core.Assistant.answer] method is where you put the logic to access your LLM.
# This could call an API directly, call other member functions of your assistant that call an API,
# or call a local LLM. Ragna is designed to give you that flexibility.

# %%
# Your `answer()` method should take a prompt in the form of a string, and a list of `Source`s, in addition to whatever other arguments you find necessary for your particular assistant. The return type is an `Iterator` of strings.

# %%
# ```python
#     def answer(self, prompt: str, sources: list[Source]) -> Iterator[str]:
#         yield (
#             f"This is a default answer. There were {len(sources)} sources."
#             ""
#             f"The prompt was"
#             f"{prompt}"
#         )
# ```

# %%
# !!! note
#     Ragna also supports streaming responses from the assistant. See the
#     [example how to use streaming responses](../../generated/examples/gallery_streaming.md)
#     for more information.

# %%
# See the documentation on [how to include external objects in Ragna](../../references/config.md#referencing-python-objects)

# %%
# ### Step 2: Use the Assistant in Ragna
