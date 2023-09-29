import contextlib
import io
from typing import Optional
from urllib.parse import urlsplit

import cloudpickle

import huey.api
import huey.utils
from huey.contrib.asyncio import aget_result

from ._core import RagnaException
from ._requirement import PackageRequirement


def execute(serialized_fn):
    fn = cloudpickle.loads(serialized_fn)

    # FIXME: this will only surfaces the output in case the job succeeds. While
    #  better than nothing, surfacing output in the failure cases is more important
    #  Plus, we should probably also let the output happen here
    with contextlib.redirect_stdout(
        io.StringIO()
    ) as stdout, contextlib.redirect_stderr(io.StringIO()) as stderr:
        return fn(), (stdout.getvalue(), stderr.getvalue())


class _Task(huey.api.Task):
    def execute(self):
        (serialized_fn,) = self.args
        return execute(serialized_fn)


class Queue:
    def __init__(self, url: Optional[str] = None):
        name = "ragna"
        if url is None:
            huey_ = huey.MemoryHuey(name=name, immediate=True)
        else:
            components = urlsplit(url)
            if components.scheme in {"", "file"}:
                huey_ = huey.FileHuey(name=name, path=components.path)
            elif components.scheme in {"redis", "rediss"}:
                if not PackageRequirement("redis").is_available():
                    raise RagnaException("redis not installed")
                import redis

                huey_ = huey.RedisHuey(name=name, url=url)
                try:
                    huey_.storage.conn.ping()
                except redis.exceptions.ConnectionError:
                    raise RagnaException("Unable to connect to redis", url=url)
            else:
                raise RagnaException("Unknown URL scheme", url=url)
        self._huey = huey_
        # This is registering the execute function above to be called if a task is
        # enqueued. We need to create the TaskWrapper object here, because this is the
        # only way to dynamically register tasks while staying in the public API. This
        # could be replaced by
        # self._huey._registry._registry[f"{__name__}.{_Task.__name__}"] = _Task
        huey.api.TaskWrapper(self._huey, execute, name=_Task.__name__)

    async def enqueue(self, fn, **task_kwargs):
        task = _Task(args=(cloudpickle.dumps(fn),), **task_kwargs)
        result = self._huey.enqueue(task)
        output = await aget_result(result)
        if isinstance(output, huey.utils.Error):
            raise RagnaException("Task failed", **output.metadata)
        return_value, (stdout, stderr) = output
        return return_value

    def create_worker(self, num_workers: int = 1):
        return self._huey.create_consumer(workers=num_workers)
