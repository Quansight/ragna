from __future__ import annotations

import enum
import textwrap
from typing import Any, Literal, Sequence, Union, cast

import pydantic
import pydantic_core


class MetadataOperator(enum.Enum):
    """
    ADDME
    """

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
    """
    ADDME
    """

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

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, MetadataFilter):
            return NotImplemented

        if self.operator != other.operator:
            return False

        if self.operator in {MetadataOperator.AND, MetadataOperator.OR}:
            if len(self.value) != len(other.value):
                return False

            for self_child, other_child in zip(self.value, other.value):
                if self_child != other_child:
                    return False

            return True
        else:
            return (self.key == other.key) and (self.value == other.value)

    def to_primitive(self) -> dict[str, Any]:
        if self.operator is MetadataOperator.RAW:
            value = self.value
        elif self.operator in {MetadataOperator.AND, MetadataOperator.OR}:
            value = [child.to_primitive() for child in self.value]
        else:
            value = {self.key: self.value}

        return {self.operator.name: value}

    @classmethod
    def from_primitive(cls, obj: dict[str, Any]) -> MetadataFilter:
        operator, value = next(iter(obj.items()))
        operator = MetadataOperator.__members__[operator.upper()]
        if operator is MetadataOperator.RAW:
            key = ""
        elif operator in {MetadataOperator.AND, MetadataOperator.OR}:
            key = ""
            value = [cls.from_primitive(child) for child in value]
        else:
            key, value = next(iter(cast(dict[str, Any], value).items()))

        return cls(operator, key, value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: pydantic.GetCoreSchemaHandler
    ) -> pydantic_core.CoreSchema:
        def validate(value: Union[MetadataFilter, dict[str, Any]]) -> MetadataFilter:
            if isinstance(value, MetadataFilter):
                return value
            else:
                return cls.from_primitive(value)

        def serialize(value: Union[MetadataFilter, dict[str, Any]]) -> dict[str, Any]:
            if isinstance(value, MetadataFilter):
                return value.to_primitive()
            else:
                return value

        dict_schema = pydantic_core.core_schema.dict_schema(
            keys_schema=pydantic_core.core_schema.literal_schema(
                list(MetadataOperator.__members__)
            ),
        )
        return pydantic_core.core_schema.no_info_after_validator_function(
            # allowed input schemas
            schema=pydantic_core.core_schema.union_schema(
                [
                    pydantic_core.core_schema.is_instance_schema(cls),
                    dict_schema,
                ]
            ),
            # function to be applied after the input schema check
            function=validate,
            serialization=pydantic_core.core_schema.plain_serializer_function_ser_schema(
                function=serialize,
                return_schema=dict_schema,
                when_used="json",
            ),
        )

    @classmethod
    def raw(cls, value: Any) -> MetadataFilter:
        return cls(MetadataOperator.RAW, "", value)

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
            "",
            cls._flatten(MetadataOperator.AND, children),
        )

    @classmethod
    def or_(cls, children: list[MetadataFilter]) -> MetadataFilter:
        return cls(
            MetadataOperator.OR,
            "",
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
