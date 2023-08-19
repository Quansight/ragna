from ragna.extensions import Document, hookimpl, Llm, Source, SourceStorage


class RagnaDemoSourceStorage(SourceStorage):
    @classmethod
    def display_name(cls):
        return "ragna/DemoDocDb"

    def __init__(self, app_config):
        super().__init__(app_config)
        self._document_metadatas = {}

    def store(self, documents: list[Document], chat_config) -> None:
        self._document_metadatas[self.app_config.user] = [
            document.metadata for document in documents
        ]

    def retrieve(self, prompt: str, *, num_tokens: int, chat_config) -> list[Source]:
        return [
            Source(
                document_name=metadata.name,
                page_numbers="N/A",
                text="I'm just pretending here",
                num_tokens=-1,
            )
            for metadata in self._document_metadatas[self.app_config.user]
        ]


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

    def complete(self, prompt: str, sources: list[Source], *, chat_config) -> str:
        return "This is a demo completion"


@hookimpl(specname="ragna_llm")
def ragna_demo_llm():
    return RagnaDemoLlm
