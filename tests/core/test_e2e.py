import asyncio
import contextlib
import platform
import shutil
import sys
import time

import pytest

import ragna.core
import redis
from ragna import Config, Rag
from ragna.assistants import RagnaDemoAssistant
from ragna.source_storages import RagnaDemoSourceStorage

from tests.utils import background_subprocess, get_available_port, timeout_after


class TestSmoke:
    async def main(self, config, documents):
        rag = Rag(config)
        chat = rag.chat(
            documents=documents,
            source_storage=RagnaDemoSourceStorage,
            assistant=RagnaDemoAssistant,
        )
        async with chat:
            return await chat.answer("?!")

    def check(self, *, config, root):
        document_root = root / "documents"
        document_root.mkdir()
        document_path = document_root / "test.txt"
        with open(document_path, "w"):
            pass

        @timeout_after()
        def main():
            return asyncio.run(self.main(config, [document_path]))

        answer = main()

        assert isinstance(answer, ragna.core.Message)
        assert answer.role is ragna.core.MessageRole.ASSISTANT
        assert {source.document.name for source in answer.sources} == {
            document_path.name
        }

    def test_memory_queue(self, tmp_path):
        self.check(config=Config(rag=dict(queue_url="memory")), root=tmp_path)

    @contextlib.contextmanager
    def worker(self, *, config):
        config_path = config.local_cache_root / "ragna.toml"
        config.to_file(config_path)

        with background_subprocess(
            [sys.executable, "-m", "ragna", "worker", "--config", str(config_path)]
        ) as process:

            @timeout_after(message="Unable to start worker")
            def wait_for_worker():
                # This seems quite brittle, but I didn't find a better way to check
                # whether the worker is ready. We are checking the logged messages until
                # we see the "ready" message.
                for line in process.stderr:
                    sys.stderr.buffer.write(line)
                    if b"Huey consumer started" in line:
                        sys.stderr.flush()
                        return

            wait_for_worker()
            yield

    @pytest.mark.parametrize("scheme", ["", "file://"])
    def test_file_system_queue(self, tmp_path, scheme):
        config = Config(
            local_cache_root=tmp_path,
            rag=dict(queue_url=f"{scheme}{(tmp_path / 'queue').as_posix()}"),
        )

        with self.worker(config=config):
            self.check(config=config, root=tmp_path)

    @contextlib.contextmanager
    def redis_server(self, scheme="redis://"):
        if platform.system() == "Windows":
            pytest.skip("redis-server is not available for Windows")

        port = get_available_port()
        url = f"{scheme}127.0.0.1:{port}"
        redis_server_executable = shutil.which("redis-server")
        if redis_server_executable is None:
            raise RuntimeError("Unable to find redis-server executable")

        with background_subprocess([redis_server_executable, "--port", str(port)]):
            connection = redis.Redis.from_url(url)

            @timeout_after(message=f"Unable to establish connection to {url}")
            def wait_for_redis_server(poll=0.1):
                while True:
                    with contextlib.suppress(redis.ConnectionError):
                        if connection.ping():
                            return

                    time.sleep(poll)

            wait_for_redis_server()
            yield url

    # TODO: Find a way to redis with TLS connections, i.e. the rediss:// scheme
    @pytest.mark.parametrize("scheme", ["redis://"])
    def test_redis_queue(self, tmp_path, scheme):
        with self.redis_server(scheme) as queue_url:
            config = Config(local_cache_root=tmp_path, rag=dict(queue_url=queue_url))

            with self.worker(config=config):
                self.check(config=config, root=tmp_path)
