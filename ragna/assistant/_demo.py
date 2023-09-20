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
        I just pretend to be an LLM. I can't actually help with your prompt:
        
        > {prompt}
        
        I was given the following sources:
        
        {sources}
        """
            )
            .strip()
            .format(name=str(self), prompt=prompt, sources="\n".join(sources_display))
        )
