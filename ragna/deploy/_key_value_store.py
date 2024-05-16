from __future__ import annotations

import abc
import os
from typing import Any, Generic, Optional, TypeVar

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
    def serialize(self, model: M) -> str:
        return SerializableModel.from_model(model).model_dump_json()

    def deserialize(self, json_str: str) -> M:
        return SerializableModel.model_validate_json(json_str).to_model()

    @abc.abstractmethod
    def __setitem__(self, key: str, model: M) -> None: ...

    @abc.abstractmethod
    def __getitem__(self, key: str) -> M: ...

    @abc.abstractmethod
    def __delitem__(self, key: str) -> None: ...

    def get(self, key: str, default: Optional[M] = None) -> Optional[M]:
        try:
            return self[key]
        except KeyError:
            return default


class InMemoryKeyValueStore(KeyValueStore[M]):
    def __init__(self) -> None:
        self._store: dict[str, M] = {}

    def __setitem__(self, key: str, model: M) -> None:
        self._store[key] = model

    def __getitem__(self, key: str) -> M:
        return self._store[key]

    def __delitem__(self, key: str) -> None:
        del self._store[key]


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

    def __setitem__(self, key: str, model: M) -> None:
        self._r[key] = self.serialize(model)

    def __getitem__(self, key: str) -> M:
        return self.deserialize(self._r[key])

    def __delitem__(self, key: str) -> None:
        del self._r[key]
