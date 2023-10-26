import asyncio
import contextlib

import pytest

import ragna.core
from ragna import Config, Rag
from ragna.assistants import RagnaDemoAssistant
from ragna.source_storages import RagnaDemoSourceStorage
from tests.utils import ragna_worker, redis_server, skip_redis_on_windows, timeout_after


@pytest.mark.parametrize(
    "queue",
    ["memory", "file_system", pytest.param("redis", marks=skip_redis_on_windows)],
)
def test_e2e(tmp_path, queue):
    if queue == "memory":
        queue_cm = contextlib.nullcontext("memory")
        worker_cm_fn = contextlib.nullcontext
    elif queue == "file_system":
        queue_cm = contextlib.nullcontext(str(tmp_path / "queue"))
        worker_cm_fn = ragna_worker
    elif queue == "redis":
        queue_cm = redis_server()
        worker_cm_fn = ragna_worker

    with queue_cm as queue_url:
        config = Config(
            local_cache_root=tmp_path,
            core=dict(queue_url=queue_url),
        )
        with worker_cm_fn(config):
            check_core(config)


@timeout_after()
def check_core(config):
    document_root = config.local_cache_root / "documents"
    document_root.mkdir()
    document_path = document_root / "test.txt"
    with open(document_path, "w") as file:
        file.write("!\n")

    async def core():
        rag = Rag(config)
        chat = rag.chat(
            documents=[document_path],
            source_storage=RagnaDemoSourceStorage,
            assistant=RagnaDemoAssistant,
        )
        async with chat:
            return await chat.answer("?")

    answer = asyncio.run(core())

    assert isinstance(answer, ragna.core.Message)
    assert answer.role is ragna.core.MessageRole.ASSISTANT
    assert {source.document.name for source in answer.sources} == {document_path.name}
