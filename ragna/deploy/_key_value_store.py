from __future__ import annotations

import abc
import os
import time
from typing import Any, Callable, Generic, Optional, TypeVar, Union, cast

import pydantic

from ragna.core import PackageRequirement, Requirement
from ragna.core._utils import RequirementsMixin

M = TypeVar("M", bound=pydantic.BaseModel)


class SerializableModel(pydantic.BaseModel, Generic[M]):
    cls: pydantic.ImportString[type[M]]
    obj: dict[str, Any]

    @classmethod
    def from_model(cls, model: M) -> SerializableModel[M]:
        return SerializableModel(cls=type(model), obj=model.model_dump(mode="json"))

    def to_model(self) -> M:
        return self.cls.model_validate(self.obj)


class KeyValueStore(abc.ABC, RequirementsMixin, Generic[M]):
    """
    ADDME
    """

    def serialize(self, model: M) -> str:
        return SerializableModel.from_model(model).model_dump_json()

    def deserialize(self, data: Union[str, bytes]) -> M:
        return SerializableModel.model_validate_json(data).to_model()

    @abc.abstractmethod
    def set(
        self, key: str, model: M, *, expires_after: Optional[int] = None
    ) -> None: ...

    @abc.abstractmethod
    def get(self, key: str) -> Optional[M]: ...

    @abc.abstractmethod
    def delete(self, key: str) -> None: ...

    @abc.abstractmethod
    def refresh(self, key: str, *, expires_after: Optional[int] = None) -> None: ...


class InMemoryKeyValueStore(KeyValueStore[M]):
    def __init__(self) -> None:
        self._store: dict[str, tuple[M, Optional[float]]] = {}
        self._timer: Callable[[], float] = time.monotonic

    def set(self, key: str, model: M, *, expires_after: Optional[int] = None) -> None:
        if expires_after is not None:
            expires_at = self._timer() + expires_after
        else:
            expires_at = None
        self._store[key] = (model, expires_at)

    def get(self, key: str) -> Optional[M]:
        value = self._store.get(key)
        if value is None:
            return None

        model, expires_at = value
        if expires_at is not None and self._timer() >= expires_at:
            self.delete(key)
            return None

        return model

    def delete(self, key: str) -> None:
        if key not in self._store:
            return

        del self._store[key]

    def refresh(self, key: str, *, expires_after: Optional[int] = None) -> None:
        value = self._store.get(key)
        if value is None:
            return

        model, _ = value
        self.set(key, model, expires_after=expires_after)


class RedisKeyValueStore(KeyValueStore[M]):
    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [PackageRequirement("redis")]

    def __init__(self) -> None:
        import redis

        self._r = redis.Redis(
            host=os.environ.get("RAGNA_REDIS_HOST", "localhost"),
            port=int(os.environ.get("RAGNA_REDIS_PORT", 6379)),
        )

    def set(self, key: str, model: M, *, expires_after: Optional[int] = None) -> None:
        self._r.set(key, self.serialize(model), ex=expires_after)

    def get(self, key: str) -> Optional[M]:
        value = cast(bytes, self._r.get(key))
        if value is None:
            return None
        return self.deserialize(value)

    def delete(self, key: str) -> None:
        self._r.delete(key)

    def refresh(self, key: str, *, expires_after: Optional[int] = None) -> None:
        if expires_after is None:
            self._r.persist(key)
        else:
            self._r.expire(key, expires_after)
