from ora.extensions import DocDB, hookimpl, LLM


class OraDemoDocDB(DocDB):
    @classmethod
    def display_name(cls):
        return "ora/DemoDocDb"

    def store(self, documents: list) -> None:
        pass

    def retrieve(self, prompt: str, *, chat_config) -> list:
        return ["demo retrieval"]


@hookimpl(specname="ora_doc_db")
def ora_demo_doc_db():
    return OraDemoDocDB


class OraDemoLLM(LLM):
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
    return OraDemoLLM
