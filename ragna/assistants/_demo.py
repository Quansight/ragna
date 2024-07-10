import textwrap
from typing import Iterator

from ragna.core import Assistant, Message, MessageRole


class RagnaDemoAssistant(Assistant):
    """Demo assistant without requirements.

    !!! note

        As the name implies, this assistant is just for demo purposes and cannot
        answer any questions. By default it replies with the prompt and the given
        sources.

        If you include the phrase `"markdown"` into your prompt, it will return a
        Markdown table including emojis.
    """

    @classmethod
    def display_name(cls) -> str:
        return "Ragna/DemoAssistant"

    def answer(self, messages: list[Message]) -> Iterator[str]:
        if "markdown" in messages[-1].content.lower():
            yield self._markdown_answer()
        else:
            yield self._default_answer(messages)

    def _markdown_answer(self) -> str:
        return textwrap.dedent(
            """
            | String | Integer  | Float | Emoji              |
            | :----- | :------: | ----: | ------------------ |
            | foo    | 0        | 1.0   | :unicorn:          |
            | `bar`  | 1        | -1.23 | :metal:            |
            | "baz"  | -1       | 1e6   | :eye: :lips: :eye: |
            """
        ).strip()

    def _default_answer(self, messages: list[Message]) -> str:
        prompt, sources = (message := messages[-1]).content, message.sources
        sources_display = []
        for source in sources:
            source_display = f"- {source.document.name}"
            if source.location:
                source_display += f", {source.location}"
            source_display += f": {textwrap.shorten(source.content, width=100)}"
            sources_display.append(source_display)
        if len(sources) > 3:
            sources_display.append("[...]")

        n_messages = len([m for m in messages if m.role == MessageRole.USER])
        return (
            textwrap.dedent(
                """
                I'm a demo assistant and can be used to try Ragna's workflow.
                I will only mirror back my inputs. 

                So far I have received {n_messages} messages.
                
                Your last prompt was:

                > {prompt}

                These are the sources I was given:

                {sources}
                """
            )
            .strip()
            .format(
                name=str(self),
                n_messages=n_messages,
                prompt=prompt,
                sources="\n".join(sources_display),
            )
        )
