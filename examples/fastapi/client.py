from ragna.extensions import (
    hookimpl,
    Llm,
    PackageRequirement,
    ragna_demo_source_storage,  # noqa
    Requirement,
    Source,
)
from ragna.extensions.page_extractor import *  # noqa


class ExampleLlmRestApi(Llm):
    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [PackageRequirement("requests")]

    @property
    def context_size(self) -> int:
        return 1_000

    def complete(self, prompt: str, sources: list[Source], *, chat_config):
        import requests

        return requests.post(
            "http://localhost:8888/complete",
            json={"prompt": prompt, "sources": [source.text for source in sources]},
        ).json()


@hookimpl
def ragna_llm():
    return ExampleLlmRestApi
