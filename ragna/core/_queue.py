import asyncio
import contextlib
import io
import shutil
import subprocess
import sys
import time
from typing import Any, Callable, Optional, TypeVar
from urllib.parse import urlsplit

import cloudpickle
from redis import ConnectionError, Redis
from rq import Queue, Worker as _Worker
from rq.worker_pool import WorkerPool as _WorkerPool

from ._core import RagnaException

T = TypeVar("T")


def _get_queue(url, *, start_redis_server):
    connection, redis_server_proc = _get_connection(
        url, start_redis_server=start_redis_server
    )
    return Queue(connection=connection), redis_server_proc


def _get_connection(url, *, start_redis_server, startup_timeout=5) -> tuple[Redis, Any]:
    try:
        connection = Redis.from_url(url)
        connection.ping()
    except ConnectionError:
        connection = None

    if connection is None and start_redis_server is False:
        raise RagnaException("redis is not running")
    elif connection is not None and start_redis_server is True:
        raise RagnaException("redis is already running")
    elif connection is not None:
        return connection, None

    url_components = urlsplit(url)
    if url_components.hostname not in {"localhost", "127.0.0.1"}:
        raise RagnaException("Can only start on localhost")
    # FIXME: check if port is open
    # with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
    #     if sock.connect_ex((url_components.hostname, url_components.port)):
    #         raise RagnaException(f"Port {url_components.port} is already in use")

    redis_server_executable = shutil.which("redis-server")
    if redis_server_executable is None:
        with contextlib.suppress(ModuleNotFoundError):
            import redis_server

            redis_server_executable = redis_server.REDIS_SERVER_PATH

    if redis_server_executable is None:
        raise RagnaException("Can't find redis-server executable")

    proc = subprocess.Popen(
        [redis_server_executable, "--port", str(url_components.port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        connection = Redis.from_url(url)

        start = time.time()
        while (time.time() - start) < startup_timeout:
            if connection.ping():
                break

            time.sleep(0.5)
            time.perf_counter()
        else:
            raise RagnaException()
    except (ConnectionError, RagnaException) as error:
        proc.kill()
        stdout, stderr = proc.communicate()
        raise RagnaException(
            f"Unable to start redis-server. {stdout} {stderr}"
        ) from error

    return connection, proc


async def _enqueue_job(
    queue: Queue, fn: Callable[[], T], **job_kwargs: Any
) -> Optional[T]:
    job = queue.enqueue(Worker._execute_job, cloudpickle.dumps(fn), **job_kwargs)
    # FIXME: There is a way to get a notification from redis if the job is done.
    #   We should prefer that over polling.
    # -> pubsub
    while True:
        status = job.get_status()
        if status == "finished":
            return_value = job.return_value()
            if return_value is None:
                return return_value

            result, (stdout, stderr) = return_value
            sys.stdout.write(stdout)
            sys.stderr.write(stderr)
            return result
        elif status == "failed":
            return "failed"
        await asyncio.sleep(0.2)


class Worker:
    def __init__(self, *, queue_database_url: str, num_workers: int = 1):
        queue, _ = _get_queue(queue_database_url, start_redis_server=False)
        queues = [queue]
        connection = queue.connection
        if num_workers == 1:
            self._start_fn = _Worker(queues=queues, connection=connection).work
        else:
            self._start_fn = _WorkerPool(
                queues=queues, connection=connection, num_workers=num_workers
            ).start

    def start(self, **kwargs):
        return self._start_fn(**kwargs)

    @staticmethod
    def _execute_job(cloudpickled_fn: bytes) -> Any:
        fn = cloudpickle.loads(cloudpickled_fn)

        # FIXME: this will only surfaces the output in case the job succeeds. While
        #  better than nothing, surfacing output in the failure cases is more important
        #  Plus, we should probably also let the output happen here
        with contextlib.redirect_stdout(
            io.StringIO()
        ) as stdout, contextlib.redirect_stderr(io.StringIO()) as stderr:
            return fn(), (stdout.getvalue(), stderr.getvalue())
