import os
import sys
from pathlib import Path

from ragna2.core import Config, Document, Llm, Rag, Source, SourceStorage


os.environ["OPENAI_API_KEY"] = "foo"


class RagnaDemoSourceStorage(SourceStorage):
    @classmethod
    def display_name(cls):
        return "Ragna/DemoSourceStorage"

    def __init__(self, config):
        super().__init__(config)
        self._document_names = {}

    def store(self, documents: list[Document]) -> None:
        # FIXME: we need to take the chat id as parameter and use that as key
        self._document_names[""] = [document.name for document in documents]

    def retrieve(self, prompt: str) -> list[Source]:
        return [
            Source(
                document_name=name,
                page_numbers="N/A",
                text=(
                    text := f"I'm pretending to be a chunk of text from inside {name}."
                ),
                num_tokens=len(text.split()),
            )
            for name in self._document_names
        ]


class RagnaDemoLlm(Llm):
    @classmethod
    def display_name(cls):
        return "Ragna/DemoLLM"

    @property
    def context_size(self) -> int:
        return sys.maxsize

    def complete(self, prompt: str, sources: list[Source]) -> str:
        return (
            "I'm just pretending to be an LLM, "
            "so I can't actually help with your prompt."
        )


def fn(*args):
    return sum(args)


async def main():
    config = Config()

    print(config)

    rag = Rag(config, start_ragna_worker=False, start_redis_server=False)

    chat = await rag.start_new_chat(
        documents=list(Path.cwd().glob("*.py")),
        source_storage=RagnaDemoSourceStorage,
        llm=RagnaDemoLlm,
    )

    answer = await chat.answer("Who is the CEO?")

    print(answer)


# WHAT IS A FREAKIN DOCUMENT?

# inside state: one user,

# outside:
# we need to be


if __name__ == "__main__":
    # import io
    # import contextlib
    #
    # with contextlib.redirect_stdout(io.StringIO()) as stdout:
    #     print("foo")
    #     a = stdout.getvalue()
    # print(a)

    # asyncio.run(main())
    # from rq import Queue
    # from rq.job import Job
    # from redis import Redis
    # import time
    #
    # q = Queue(connection=Redis())
    #
    # job = q.enqueue("main2.fn")
    #
    # time.sleep(0.5)
    # print(job.get_status(), job.exc_info)
    #
    # # from rq.registry import FailedJobRegistry
    # #
    # # registry = FailedJobRegistry(queue=q)
    # #
    # # for job_id in registry.get_job_ids():
    # #     print(job_id)
    # #     # job = Job.fetch(job_id, connection=q.connection)
    # #     # print(job_id, job.exc_info)

    from collections import defaultdict

    from pydantic import BaseModel, create_model

    class Model1(BaseModel):
        a: int
        b: str = "default"

    class Model2(BaseModel):
        c: float
        d: str = "another default"

    class Model3(BaseModel):
        a: int = 5
        d: str

    def merge_models(model_name, *models):
        raw_field_definitions = defaultdict(list)
        for model_cls in models:
            for name, field in model_cls.__fields__.items():
                raw_field_definitions[name].append(
                    (field.type_, ... if field.required else field.default)
                )

        field_definitions = {}
        for name, definitions in raw_field_definitions.items():
            if len(definitions) == 1:
                field_definitions[name] = definitions[0]
                continue

            types, defaults = zip(*definitions)

            types = set(types)
            if len(types) > 1:
                raise Exception(f"Mismatching types for field {name}: {types}")
            type_ = types.pop()

            if any(default is ... for default in defaults):
                default = ...
            else:
                defaults = set(defaults)
                if len(defaults) == 1:
                    default = defaults.pop()
                else:
                    # FIXME: This branch is hit if a parameter is optional for all models,
                    #  but we have mismatching defaults. We need to put a sentinel here that
                    #  indicates that the downstream model, i.e. one of the models we are
                    #  currently merging needs to take their default
                    raise Exception(
                        f"Mismatching defaults for field {name}: {defaults}"
                    )

            field_definitions[name] = (type_, default)

        return create_model(model_name, **field_definitions)

    MergedModel = merge_models("MergedModel", Model1, Model2, Model3)

    assert MergedModel.__fields__.keys() == set("abcd")
    assert MergedModel.__fields__["a"].required
    assert (
        not (field := MergedModel.__fields__["b"]).required
        and field.default == "default"
    )
    assert MergedModel.__fields__["c"].required
    assert MergedModel.__fields__["d"].required
