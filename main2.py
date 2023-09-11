import asyncio

import dotenv

import ragna2.llm

import ragna2.source_storage
from ragna2.core import Config, Rag

assert dotenv.load_dotenv("../Quansight/generative-ai-expts/.env")


def fn(*args):
    return sum(args)


async def main():
    config = Config()

    rag = Rag(config, start_ragna_worker=False, start_redis_server=False)

    document = config.document_class("foo.txt")

    chat = await rag.start_new_chat(
        documents=[document],
        source_storage=ragna2.source_storage.ChromaSourceStorage,
        llm=ragna2.llm.OpenaiGpt4Llm,
    )

    answer = await chat.answer("What is Ragna?")

    print(answer)


if __name__ == "__main__":
    # import io
    # import contextlib
    #
    # with contextlib.redirect_stdout(io.StringIO()) as stdout:
    #     print("foo")
    #     a = stdout.getvalue()
    # print(a)

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

    # from collections import defaultdict
    #
    # from pydantic import BaseModel, create_model
    #
    # class Model1(BaseModel):
    #     a: int
    #     b: str = "default"
    #
    # class Model2(BaseModel):
    #     c: float
    #     d: str = "another default"
    #
    # class Model3(BaseModel):
    #     a: int = 5
    #     d: str
    #     b: str = "default?"
    #
    # def merge_models(model_name, *models):
    #     raw_field_definitions = defaultdict(list)
    #     for model_cls in models:
    #         for name, field in model_cls.__fields__.items():
    #             raw_field_definitions[name].append(
    #                 (field.type_, ... if field.required else field.default)
    #             )
    #
    #     field_definitions = {}
    #     for name, definitions in raw_field_definitions.items():
    #         if len(definitions) == 1:
    #             field_definitions[name] = definitions[0]
    #             continue
    #
    #         types, defaults = zip(*definitions)
    #
    #         types = set(types)
    #         if len(types) > 1:
    #             raise Exception(f"Mismatching types for field {name}: {types}")
    #         type_ = types.pop()
    #
    #         if any(default is ... for default in defaults):
    #             default = ...
    #         else:
    #             defaults = set(defaults)
    #             if len(defaults) == 1:
    #                 default = defaults.pop()
    #             else:
    #                 default = None
    #
    #         field_definitions[name] = (type_, default)
    #
    #     return create_model(model_name, **field_definitions)
    #
    # MergedModel = merge_models("MergedModel", Model1, Model2, Model3)
    #
    # print(MergedModel.schema_json())
    #
    # assert MergedModel.__fields__.keys() == set("abcd")
    # assert MergedModel.__fields__["a"].required
    # assert not (field := MergedModel.__fields__["b"]).required and field.default is None
    # assert MergedModel.__fields__["c"].required
    # assert MergedModel.__fields__["d"].required
