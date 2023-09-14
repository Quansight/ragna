import sys
import textwrap

from ragna.core import Llm, Source


class RagnaDemoLlm(Llm):
    @classmethod
    def display_name(cls):
        return "Ragna/DemoLLM"

    @property
    def context_size(self) -> int:
        return sys.maxsize

    def complete(self, prompt: str, sources: list[Source]) -> str:
        sources_display = [
            (
                f"- {source.document_name}, page(s) {source.page_numbers}: "
                f"{textwrap.shorten(source.text, width=100)}"
            )
            for source in sources[:3]
        ]
        if len(sources) > 3:
            sources_display.append("[...]")

        return textwrap.dedent(
            """
        I'm {name} and I just pretend to be an LLM. I can't actually help with your prompt:
        
        > {prompt}
        
        I was given the following sources:
        
        {sources}
        """.format(
                name=str(self), prompt=prompt, sources="\n".join(sources_display)
            )
        ).strip()
