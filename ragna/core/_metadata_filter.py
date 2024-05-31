from __future__ import annotations

import enum
import json
import textwrap
from typing import Any, Literal, Sequence, cast


class MetadataOperator(enum.Enum):
    RAW = enum.auto()
    AND = enum.auto()
    OR = enum.auto()
    EQ = enum.auto()
    NE = enum.auto()
    LT = enum.auto()
    LE = enum.auto()
    GT = enum.auto()
    GE = enum.auto()
    IN = enum.auto()
    NOT_IN = enum.auto()


class MetadataFilter:
    # These are just to be consistent. The actual values have no effect.
    _RAW_KEY = "filter"
    _CHILDREN_KEY = "children"

    def __init__(self, operator: MetadataOperator, key: str, value: Any) -> None:
        self.operator = operator
        self.key = key
        self.value = value

    def __repr__(self) -> str:
        if self.operator is MetadataOperator.RAW:
            return f"{self.operator.name}({self.value!r})"
        elif self.operator in {MetadataOperator.AND, MetadataOperator.OR}:
            return "\n".join(
                [
                    f"{self.operator.name}(",
                    *[
                        f"{textwrap.indent(repr(child), prefix=' ' * 2)},"
                        for child in self.value
                    ],
                    ")",
                ]
            )
        else:
            return f"{self.operator.name}({self.key!r}, {self.value!r})"

    def _to_json(self) -> dict[str, Any]:
        if self.operator in {MetadataOperator.AND, MetadataOperator.OR}:
            value = [child._to_json() for child in self.value]
        else:
            value = self.value

        return {self.operator.name: {self.key: value}}

    def to_json(self) -> str:
        return json.dumps(self._to_json())

    @classmethod
    def _from_json(cls, json_obj: dict[str, Any]) -> MetadataFilter:
        operator, key_value = next(iter(json_obj.items()))
        operator = MetadataOperator.__members__[operator]
        key_value = cast(dict[str, Any], key_value)
        key, value = next(iter(key_value.items()))

        if operator in {MetadataOperator.AND, MetadataOperator.OR}:
            value = [cls._from_json(child) for child in value]

        return cls(operator, key, value)

    @classmethod
    def from_json(cls, json_str: str) -> MetadataFilter:
        return cls._from_json(json.loads(json_str))

    @classmethod
    def raw(cls, value: Any) -> MetadataFilter:
        return cls(MetadataOperator.RAW, cls._RAW_KEY, value)

    @staticmethod
    def _flatten(
        operator: Literal[MetadataOperator.OR, MetadataOperator.AND],
        children: Sequence[MetadataFilter],
    ) -> list[MetadataFilter]:
        flat_children = []
        for child in children:
            if child.operator == operator:
                flat_children.extend(child.value)
            else:
                flat_children.append(child)
        return flat_children

    @classmethod
    def and_(cls, children: Sequence[MetadataFilter]) -> MetadataFilter:
        return cls(
            MetadataOperator.AND,
            cls._CHILDREN_KEY,
            cls._flatten(MetadataOperator.AND, children),
        )

    @classmethod
    def or_(cls, children: list[MetadataFilter]) -> MetadataFilter:
        return cls(
            MetadataOperator.OR,
            cls._CHILDREN_KEY,
            cls._flatten(MetadataOperator.OR, children),
        )

    @classmethod
    def eq(cls, key: str, value: Any) -> MetadataFilter:
        return cls(MetadataOperator.EQ, key, value)

    @classmethod
    def ne(cls, key: str, value: Any) -> MetadataFilter:
        return cls(MetadataOperator.NE, key, value)

    @classmethod
    def lt(cls, key: str, value: Any) -> MetadataFilter:
        return cls(MetadataOperator.LT, key, value)

    @classmethod
    def le(cls, key: str, value: Any) -> MetadataFilter:
        return cls(MetadataOperator.LE, key, value)

    @classmethod
    def gt(cls, key: str, value: Any) -> MetadataFilter:
        return cls(MetadataOperator.GT, key, value)

    @classmethod
    def ge(cls, key: str, value: Any) -> MetadataFilter:
        return cls(MetadataOperator.GE, key, value)

    @classmethod
    def in_(cls, key: str, value: Any) -> MetadataFilter:
        return cls(MetadataOperator.IN, key, value)

    @classmethod
    def not_in(cls, key: str, value: Any) -> MetadataFilter:
        return cls(MetadataOperator.NOT_IN, key, value)
