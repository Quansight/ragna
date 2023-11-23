import re
import sys
import textwrap

from ragna.core import Assistant, Source


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

    @property
    def max_input_size(self) -> int:
        return sys.maxsize

    def answer(self, prompt: str, sources: list[Source]) -> str:
        if re.search("markdown", prompt, re.IGNORECASE):
            return self._markdown_answer()
        else:
            return self._default_answer(prompt, sources)

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

    def _default_answer(self, prompt: str, sources: list[Source]) -> str:
        sources_display = []
        for source in sources:
            source_display = f"- {source.document.name}"
            if source.location:
                source_display += f", {source.location}"
            source_display += f": {textwrap.shorten(source.content, width=100)}"
            sources_display.append(source_display)
        if len(sources) > 3:
            sources_display.append("[...]")

        return (
            textwrap.dedent(
                """
                I'm a demo assistant and can be used to try Ragnas workflow. I will only
                mirror back my inputs. 
                
                Your prompt was:

                > {prompt}

                These are the sources I was given:

                {sources}
                """
            )
            .strip()
            .format(name=str(self), prompt=prompt, sources="\n".join(sources_display))
        )
