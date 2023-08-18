from ragna.extensions import Document, hookimpl, Llm, Source, SourceStorage


class RagnaDemoSourceStorage(SourceStorage):
    @classmethod
    def display_name(cls):
        return "ragna/DemoDocDb"

    def store(self, documents: list[Document], chat_config) -> None:
        pass

    def retrieve(self, prompt: str, *, num_tokens: int, chat_config) -> list:
        return ["demo retrieval"]


@hookimpl(specname="ragna_source_storage")
def ragna_demo_source_storage():
    return RagnaDemoSourceStorage


class RagnaDemoLlm(Llm):
    @classmethod
    def display_name(cls):
        return "ragna/DemoLLM"

    @property
    def context_size(self) -> int:
        return 8_192

    def complete(self, prompt: str, sources: list[Source], *, chat_config):
        return "This is a demo completion"


@hookimpl(specname="ragna_llm")
def ragna_demo_llm():
    return RagnaDemoLlm
