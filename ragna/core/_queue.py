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
    return fn()


class _Task(huey.api.Task):
    def execute(self):
        (serialized_fn,) = self.args
        return execute(serialized_fn)


class Queue:
    def __init__(self, url: Optional[str] = None):
        # FIXME: we need to store_none=True here. SourceStorage.store returns None and
        #  if we wouldn't store it, waiting for a result is timing out. Maybe there is a
        #  better way to do this?
        common_kwargs = dict(name="ragna", store_none=True)
        if url is None:
            huey_ = huey.MemoryHuey(immediate=True, **common_kwargs)
        else:
            components = urlsplit(url)
            if components.scheme in {"", "file"}:
                huey_ = huey.FileHuey(path=components.path, **common_kwargs)
            elif components.scheme in {"redis", "rediss"}:
                if not PackageRequirement("redis").is_available():
                    raise RagnaException("redis not installed")
                import redis

                huey_ = huey.RedisHuey(url=url, **common_kwargs)
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
        return output

    def create_worker(self, num_workers: int = 1):
        return self._huey.create_consumer(workers=num_workers)
