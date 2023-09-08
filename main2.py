import asyncio

import os
from pathlib import Path

from ragna2.core import Config, Document, Rag, Source, SourceStorage

from ragna2.llm import OpenaiGpt4Llm

os.environ["OPENAI_API_KEY"] = "foo"


class RagnaDemoSourceStorage(SourceStorage):
    @classmethod
    def display_name(cls):
        return "ragna/DemoDocDb"

    def __init__(self, app_config):
        super().__init__(app_config)
        self._document_names = {}

    def store(self, documents: list[Document], user: str = "root") -> None:
        pass

    def retrieve(
        self, prompt: str, *, num_tokens: int = 2048, user: str = "root"
    ) -> list[Source]:
        return [
            Source(
                document_name="foo.pdf",
                page_numbers="N/A",
                text="I'm just pretending here",
                num_tokens=-1,
            )
        ]


def fn(*args):
    return sum(args)


async def main():
    config = Config()

    config.register_component(RagnaDemoSourceStorage)
    config.register_component(OpenaiGpt4Llm)

    print(config)

    rag = Rag(config, start_ragna_worker=False, start_redis_server=False)

    chat = await rag.start_new_chat(
        documents=[config.document_class(path) for path in Path.cwd().glob("*.py")],
        # FIXME: make this more convenient, allow str but also classes and maybe even instances?
        source_storage_name=RagnaDemoSourceStorage.display_name(),
        llm_name=OpenaiGpt4Llm.display_name(),
    )

    answer = await chat.answer("Who is the CEO?")

    print(answer)


# WHAT IS A FREAKIN DOCUMENT?

# inside state: one user,

# outside:
# we need to be


if __name__ == "__main__":
    asyncio.run(main())
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
