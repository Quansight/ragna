import itertools
from typing import Optional, Type, Union
from urllib.parse import urlsplit

import huey.api
import huey.utils
from huey.contrib.asyncio import aget_result

from ._components import Component
from ._config import Config

from ._utils import PackageRequirement, RagnaException


def task_config(retries: int = 0, retry_delay: int = 0):
    def decorator(fn):
        fn.__ragna_task_config__ = dict(retries=retries, retry_delay=retry_delay)
        return fn

    return decorator


_COMPONENTS: dict[Type[Component], Component] = {}


def execute(component, fn, args, kwargs):
    self = _COMPONENTS[component]
    return fn(self, *args, **kwargs)


class _Task(huey.api.Task):
    def execute(self):
        return execute(*self.args)


class Queue:
    def __init__(self, config: Config, *, load_components: Optional[bool]):
        self._config = config
        self._huey = self._load_huey(config.rag.queue_url)

        if load_components is None:
            load_components = isinstance(self._huey, huey.MemoryHuey)
        if load_components:
            for component in itertools.chain(
                config.rag.source_storages, config.rag.assistants
            ):
                self.load_component(component)

    def _load_huey(self, url: Optional[str]):
        # FIXME: we need to store_none=True here. SourceStorage.store returns None and
        #  if we wouldn't store it, waiting for a result is timing out. Maybe there is a
        #  better way to do this?
        common_kwargs = dict(name="ragna", store_none=True)
        if url == "memory":
            _huey = huey.MemoryHuey(immediate=True, **common_kwargs)
        else:
            components = urlsplit(url)
            if components.scheme in {"", "file"}:
                _huey = huey.FileHuey(path=components.path, **common_kwargs)
            elif components.scheme in {"redis", "rediss"}:
                if not PackageRequirement("redis").is_available():
                    raise RagnaException("redis not installed")
                import redis

                _huey = huey.RedisHuey(url=url, **common_kwargs)
                try:
                    _huey.storage.conn.ping()
                except redis.exceptions.ConnectionError:
                    raise RagnaException("Unable to connect to redis", url=url)
            else:
                raise RagnaException("Unknown URL scheme", url=url)
        # This is registering the execute function above to be called if a task is
        # enqueued. We need to create the TaskWrapper object here, because this is the
        # only way to dynamically register tasks while staying in the public API. This
        # could be replaced by
        # self._huey._registry._registry[f"{__name__}.{_Task.__name__}"] = _Task
        huey.api.TaskWrapper(_huey, execute, name=_Task.__name__)

        return _huey

    def load_component(
        self, component: Union[Type[Component], Component, str]
    ) -> Type[Component]:
        if isinstance(component, type) and issubclass(component, Component):
            cls = component
            instance = None
        elif isinstance(component, Component):
            cls = type(component)
            instance = component
        elif isinstance(component, str):
            try:
                cls = next(
                    cls for cls in _COMPONENTS if cls.display_name() == component
                )
            except StopIteration:
                raise RagnaException("Unknown component", component=component)
            instance = None

        if cls in _COMPONENTS:
            return cls

        if instance is None:
            if not cls.is_available():
                raise RagnaException("Component not available", name=cls.display_name())

            instance = cls(self._config)

        _COMPONENTS[cls] = instance

        return cls

    async def enqueue(self, component, action, args, kwargs):
        fn = getattr(component, action)
        task = _Task(
            args=(component, fn, args, kwargs),
            **getattr(fn, "__ragna_task_config__", dict()),
        )
        result = self._huey.enqueue(task)
        output = await aget_result(result)
        if isinstance(output, huey.utils.Error):
            raise RagnaException("Task failed", **output.metadata)
        return output

    def create_worker(self, num_workers: int = 1):
        return self._huey.create_consumer(workers=num_workers)
