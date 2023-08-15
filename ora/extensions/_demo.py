from ora.extensions import hookimpl, Llm, SourceStorage


class OraDemoSourceStorage(SourceStorage):
    @classmethod
    def display_name(cls):
        return "ora/DemoDocDb"

    def store(self, documents: list) -> None:
        pass

    def retrieve(self, prompt: str, *, chat_config) -> list:
        return ["demo retrieval"]


@hookimpl(specname="ora_source_storage")
def ora_demo_source_storage():
    return OraDemoSourceStorage


class OraDemoLlm(Llm):
    @classmethod
    def display_name(cls):
        return "ora/DemoLLM"

    @property
    def context_size(self) -> int:
        return 8_192

    def complete(self, prompt: str, chat_config):
        return "demo completion"


@hookimpl(specname="ora_llm")
def ora_demo_llm():
    return OraDemoLlm
