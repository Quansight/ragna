"""
# Adding an Assistant

Ragna has builtin support for [several assistants][ragna.assistants], but there may be cases where you 
want to use one that is not currently supported.

This tutorial walks you through the basics of creating an assistant for LLMs that are not
currently supported. 

!!! tip

    For organizational purposes, this tutorial is divided into steps, but you may wish to perform
    Step 2 during Step 1 for manual testing or debugging.
"""

# %%
# ## Step 1: Write the Assistant

# %%
# For this tutorial, we assume the code in this step is located in the file
# `ragna/assistants/_tutorial.py`
#
# First start by importing some necessary components. Ragna uses the `typing` library:

from typing import Iterator

# %%
# Your assistant will subclass the [`Assistant`][ragna.core.Assistant] abstract base class and
# [`Source`][ragna.core.Source] will be used to hold the documents or files sent to the LLM.

from ragna.core import Assistant, Source

# %%
# The main thing to do is to implement the `answer` abstract method. The
# [`answer`][ragna.core.Assistant.answer] method is where you put the logic to access your LLM.
# This could call an API directly, call other member functions of your assistant that call an API,
# or call a local LLM. Ragna is designed to give you that flexibility.


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
        """
        "Compute" the response to a given prompt. In this case,
        the "computation" is a default string.

        Args:
            prompt: Prompt to be answered.
            sources: Sources to use when answering answer the prompt.

        Returns:
            Answer.
        """
        return (
            f"This is a default answer. There were {len(sources)} sources."
            ""
            f"The prompt was"
            f"{prompt}"
        )


# %%
# !!! note
#     While including the `_default_answer` method seems to obfuscate the code, it is meant
#     to demonstrate that you can add multiple methods to your assistant that help compute
#     the response. Examples include calling an external API or preparing the sources to be
#     used by the model.

# %%
# ## Step 2: Include the Assistant in Ragna

# %%
# Once you have created your assistant, you must add it to the system so that Ragna recognizes it.
# To do this, add your custom assistant to the `__all__` list in the file
# `ragna/assistants/__init__.py`, and import it in the same file. An example is shown below:

# %%
# ```python
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
# !!! note
#     Although it is not a strict requirement, it is a convention that the items added to
#     `ragna/assistants/__init__.py` appear in alphabetical order.
