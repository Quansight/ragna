"""
# Adding More Assistants

Ragna has builtin support for [several assistants][ragna.assistants], but there may be cases where you 
want to use one that is not currently supported.

This tutorial walks you through the basics of creating an assistant for LLMs that are not
currently supported. 
"""

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
            f"The prompt was\n{prompt}"
        )


# %%
# The [`answer`][ragna.core.Assistant.answer] method is where you put the logic to access your LLM. This could ball an API directly, call other member functions of your assistant that call an API, or call a local LLM. Ragna is designed to give you that flexibility.
