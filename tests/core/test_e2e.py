import asyncio
import contextlib
import shutil
import subprocess
import sys
import time

import pytest
import ragna.core
import redis

from ragna import Config, Rag
from ragna.assistants import RagnaDemoAssistant
from ragna.source_storages import RagnaDemoSourceStorage

from tests.utils import get_available_port, timeout_after


class TestSmoke:
    async def main(self, config, documents):
        rag = Rag(config)
        async with rag.chat(
            documents=documents,
            source_storage=RagnaDemoSourceStorage,
            assistant=RagnaDemoAssistant,
        ) as chat:
            return await chat.answer("What is Ragna?")

    def check(self, *, config, root):
        document_root = root / "documents"
        document_root.mkdir()
        document_path = document_root / "test.txt"
        with open(document_path, "w"):
            pass

        with timeout_after():
            answer = asyncio.run(self.main(config, [document_path]))

        assert isinstance(answer, ragna.core.Message)
        assert answer.role is ragna.core.MessageRole.ASSISTANT
        assert {source.document.name for source in answer.sources} == {
            document_path.name
        }

    def test_memory_queue(self, tmp_path):
        self.check(config=Config(), root=tmp_path)

    @contextlib.contextmanager
    def worker(self, *, config):
        config_path = config.local_cache_root / "ragna.toml"
        config.to_file(config_path)

        process = subprocess.Popen(
            [sys.executable, "-m", "ragna", "worker", "--config", str(config_path)],
            stderr=subprocess.PIPE,
        )
        try:
            with timeout_after(message="Unable to start worker"):
                for line in process.stderr:
                    if b"Huey consumer started" in line:
                        break
            yield
        finally:
            process.kill()
            process.communicate()

    def test_file_system_queue(self, tmp_path):
        config = Config(
            local_cache_root=tmp_path,
            rag=ragna.core.RagConfig(queue_url=str(tmp_path / "queue")),
        )

        with self.worker(config=config):
            self.check(config=config, root=tmp_path)

    @contextlib.contextmanager
    def redis_server(self, scheme="redis://"):
        port = get_available_port()
        url = f"{scheme}127.0.0.1:{port}"
        redis_server_executable = shutil.which("redis-server")
        if redis_server_executable is None:
            raise RuntimeError("Unable to find redis-server executable")
        process = subprocess.Popen(
            [redis_server_executable, "--port", str(port)],
        )

        try:
            connection = redis.Redis.from_url(url)

            with timeout_after():
                while True:
                    with contextlib.suppress(redis.ConnectionError):
                        if connection.ping():
                            break

                    time.sleep(0.5)

            yield url
        finally:
            process.kill()
            process.communicate()

    @pytest.mark.parametrize("scheme", ["redis://"])
    def test_redis_queue(self, tmp_path, scheme):
        with self.redis_server(scheme) as queue_url:
            config = Config(
                local_cache_root=tmp_path,
                rag=ragna.core.RagConfig(queue_url=queue_url),
            )

            with self.worker(config=config):
                self.check(config=config, root=tmp_path)
