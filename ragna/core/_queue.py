import contextlib
import io

import pickle
from typing import TypeVar


# from rq import Queue, Worker as _Worker

from ._core import RagnaException

T = TypeVar("T")


# def _get_queue(url, *, start_redis_server):
#     connection, redis_server_proc = _get_connection(
#         url, start_redis_server=start_redis_server
#     )
#     return Queue(connection=connection), redis_server_proc
#
#
# def _get_connection(url, *, start_redis_server, startup_timeout=5) -> tuple[Redis, Any]:
#     try:
#         connection = Redis.from_url(url)
#         connection.ping()
#     except ConnectionError:
#         connection = None
#
#     if connection is None and start_redis_server is False:
#         raise RagnaException("redis-server is not running")
#     elif connection is not None and start_redis_server is True:
#         raise RagnaException("redis-server is already running")
#     elif connection is not None:
#         return connection, None
#
#     url_components = urlsplit(url)
#     if url_components.hostname not in {"localhost", "127.0.0.1"}:
#         raise RagnaException("Can only start redis-server on localhost")
#     # FIXME: check if port is open
#     # with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
#     #     if sock.connect_ex((url_components.hostname, url_components.port)):
#     #         raise RagnaException(f"Port {url_components.port} is already in use")
#
#     redis_server_executable = shutil.which("redis-server")
#     if redis_server_executable is None:
#         with contextlib.suppress(ModuleNotFoundError):
#             import redis_server
#
#             redis_server_executable = redis_server.REDIS_SERVER_PATH
#
#     if redis_server_executable is None:
#         raise RagnaException("Can't find redis-server executable")
#
#     proc = subprocess.Popen(
#         [redis_server_executable, "--port", str(url_components.port)],
#         stdout=subprocess.DEVNULL,
#         stderr=subprocess.DEVNULL,
#     )
#
#     connection = Redis.from_url(url)
#
#     start = time.time()
#     while (time.time() - start) < startup_timeout:
#         with contextlib.suppress(ConnectionError):
#             if connection.ping():
#                 break
#
#             time.sleep(0.5)
#     else:
#         proc.kill()
#         stdout, stderr = proc.communicate()
#         raise RagnaException(
#             "Unable to start redis-server", stdout=stdout, stderr=stderr
#         )
#
#     return connection, proc


from huey import MemoryHuey
from huey.api import Task as _Task, TaskWrapper
from huey.contrib.asyncio import aget_result
from huey.utils import Error


def execute(serialized_fn):
    fn = pickle.loads(serialized_fn)

    # FIXME: this will only surfaces the output in case the job succeeds. While
    #  better than nothing, surfacing output in the failure cases is more important
    #  Plus, we should probably also let the output happen here
    with contextlib.redirect_stdout(
        io.StringIO()
    ) as stdout, contextlib.redirect_stderr(io.StringIO()) as stderr:
        return fn(), (stdout.getvalue(), stderr.getvalue())


class Task(_Task):
    def execute(self):
        (serialized_fn,) = self.args
        return execute(serialized_fn)


class Queue:
    def __init__(self):
        # self._huey = FileHuey(
        #     "ragna", path="/home/philip/.cache/ragna/queue", immediate=True
        # )
        self._huey = MemoryHuey("ragna", immediate=True)
        # this is just for registration
        TaskWrapper(self._huey, execute, name=Task.__name__)

    async def enqueue(self, fn, **task_kwargs):
        task = Task(args=(pickle.dumps(fn),), **task_kwargs)
        result = self._huey.enqueue(task)
        output = await aget_result(result)
        if isinstance(output, Error):
            raise RagnaException("Task failed", **output.metadata)
        return_value, (stdout, stderr) = output
        return return_value


# async def _enqueue_job(
#     queue: Huey, fn: Callable[[], T], **job_kwargs: Any
# ) -> Optional[T]:
#     task = RagnaTask(args=(pickle.dumps(fn),), **job_kwargs)
#     # print(task.name, task, flush=True)
#     result = queue.enqueue(task)
#     return (await aget_result(result))[0]
#     #
#     # # FIXME: There is a way to get a notification from redis if the job is done.
#     # #   We should prefer that over polling.
#     # # -> pubsub
#     # while True:
#     #     status = job.get_status()
#     #     if status == "finished":
#     #         return_value = job.return_value()
#     #         if return_value is None:
#     #             return return_value
#     #
#     #         result, (stdout, stderr) = return_value
#     #         sys.stdout.write(stdout)
#     #         sys.stderr.write(stderr)
#     #         return result
#     #     elif status == "failed":
#     #         raise RagnaException("Job failed", traceback=job.latest_result().exc_string)
#     #     await asyncio.sleep(0.2)
#
#


class Worker:
    def __init__(self, *, num_workers: int = 1):
        import logging

        logging.basicConfig(level=logging.INFO)
        queue = Queue()

        if queue._huey.immediate:
            self._start_fn = lambda: None
        else:
            consumer = queue._huey.create_consumer(workers=num_workers)
            self._start_fn = consumer.run

        #
        # queue, _ = _get_queue(queue_database_url, start_redis_server=False)
        # queues = [queue]
        # connection = queue.connection
        # if num_workers == 1:
        #     self._start_fn = _Worker(queues=queues, connection=connection).work
        # else:
        #     self._start_fn = _WorkerPool(
        #         queues=queues, connection=connection, num_workers=num_workers
        #     ).start

    def start(self):
        return self._start_fn()
