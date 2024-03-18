"""
# Adding an Assistant

Ragna has builtin support for [several assistants][ragna.assistants], but there may be cases where you 
want to use one that is not currently supported.

This tutorial walks you through the basics of creating an assistant for LLMs that are not
currently supported. 
"""

# %%
# ## The Finished Product

# %%
# !!! note
#
#     The code snippet below only includes up to Step 1. To actually include your source
#     storage in Ragna, you must still perform Step 2.

from ragna.core import Assistant


class TutorialAssistant(Assistant):
    def answer(self, prompt, sources):
        """Answer a prompt given some sources.

        Args:
            prompt: Prompt to be answered.
            sources: Sources to use when answering answer the prompt.

        Returns:
            Answer.
        """
        yield (
            f"This is a default answer. There were {len(sources)} sources."
            ""
            f"The prompt was"
            f"{prompt}"
        )


# %%
# ## The Explanation

# %%
# !!! tip
#
#     For organizational purposes, this tutorial is divided into steps, but you may wish to perform
#     Step 2 during Step 1 for manual testing or debugging.


# %%
# ### Step 0: Import Necessary Modules

# %%
# First start by importing some necessary components.

# %%
# Your assistant will subclass the [`Assistant`][ragna.core.Assistant] abstract base class and
# [`Source`][ragna.core.Source] will be used to hold the documents or files sent to the LLM.

# %%
# ```python
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
# ```python
#     def answer(self, prompt, sources):
#         """Answer a prompt given some sources.
#
#         Args:
#             prompt: Prompt to be answered.
#             sources: Sources to use when answering answer the prompt.
#
#         Returns:
#             Answer.
#         """
#         yield (
#             f"This is a default answer. There were {len(sources)} sources."
#             ""
#             f"The prompt was"
#             f"{prompt}"
#          )
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
