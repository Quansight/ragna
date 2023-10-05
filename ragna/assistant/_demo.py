import re
import sys
import textwrap

from ragna.core import Assistant, Source


class RagnaDemoAssistant(Assistant):
    @classmethod
    def display_name(cls):
        return "Ragna/DemoAssistant"

    @property
    def max_input_size(self) -> int:
        return sys.maxsize

    def answer(self, prompt: str, sources: list[Source]) -> str:
        if re.search("markdown", prompt, re.IGNORECASE):
            return self._markdown_answer()
        else:
            return self._default_answer(prompt, sources)

    def _markdown_answer(self):
        return textwrap.dedent(
            """
            | String | Integer  | Float | Emoji              |
            | :----- | :------: | ----: | ------------------ |
            | foo    | 0        | 1.0   | :unicorn:          |
            | `bar`  | 1        | -1.23 | :metal:            |
            | "baz"  | -1       | 1e6   | :eye: :lips: :eye: |
            """
        ).strip()

    def _default_answer(self, prompt: str, sources: list[Source]) -> str:
        sources_display = []
        for source in sources:
            source_display = f"- {source.document_name}"
            if source.location:
                source_display += f", {source.location}"
            source_display += f": {textwrap.shorten(source.content, width=100)}"
            sources_display.append(source_display)
        if len(sources) > 3:
            sources_display.append("[...]")

        return (
            textwrap.dedent(
                """
                I can't really help you with your prompt:

                > {prompt}

                I can at least show you the sources that I was given:

                {sources}
                """
            )
            .strip()
            .format(name=str(self), prompt=prompt, sources="\n".join(sources_display))
        )
