"""
# Adding More Assistants

Ragna has builtin support for [several assistants][ragna.assistants], but there may be cases where you 
want to use one that is not currently supported.

This tutorial walks you through the basics of creating an assistant for LLMs that are not
currently supported. 
"""

# %%
# ## Write the Assistant

# %%
# First start by importing some necessary components:

from typing import Iterator

# %%
# Your assistant will subclass the [`Assistant`][ragna.core.Assistant] abstract base class and
# [`Source`][ragna.core.Source] will be used to hold the documents or files sent to the LLM.

from ragna.core import Assistant, Source

# %%
# Here is the finished product that we will explain below:


class TutorialAssistant(Assistant):
    """
    This is a basic assistant created for didactic purposes
    """

    def answer(self, prompt: str, sources: list[Source]) -> Iterator[str]:
        """Answer a prompt given some sources.

        Args:
            prompt: Prompt to be answered.
            sources: Sources to use when answering answer the prompt.

        Returns:
            Answer.
        """
        yield self._default_answer(prompt, sources)

    def _default_answer(self, prompt: str, sources: list[Source]) -> str:
        return (
            f"This is a default answer. There were {len(sources)} sources."
            ""
            f"The prompt was"
            f"{prompt}"
        )


# %%
# The [`answer`][ragna.core.Assistant.answer] method is where you put the logic to access your LLM.
# This could ball an API directly, call other member functions of your assistant that call an API,
# or call a local LLM. Ragna is designed to give you that flexibility.

# %%
# ## Include the Assistant in Ragna

# %%
# Once you have created your assistant, you must add it to the system so that it is recognized.
# To do this, add your custom assistant to the `__all__` list in the file
# `ragna/assistants/__init__.py`, and import it in the same file. An example is shown below
# with the assumption that our `TutorialAssistant` is located in the file
# `ragna/assistants/_tutorial`:

# %%
# ```
# __all__ = [
#     # [Other assistants...]
#     "Gpt35Turbo16k",
#     "Gpt4",
#     "TutorialAssistant",
# ]
#
# # [Other imports...]
# from ._openai import Gpt4, Gpt35Turbo16k
# from ._tutorial import TutorialAssistant
#
# # [Rest of file...]
# ```

# %%
# Although it is not a strict requirement, it is a convention that the items added to
# `ragna/assistants/__init__.py` appear in alphabetical order.
