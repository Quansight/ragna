from __future__ import annotations

import enum
import textwrap
from typing import Any, Optional, Sequence, Union, cast


class MetadataFilterOperator(enum.Enum):
    EQ = "eq"
    AND = "and"
    OR = "or"


class MetadataFilter:
    def __init__(
        self,
        operator: MetadataFilterOperator,
        *,
        key_value: Optional[tuple[str, str]] = None,
        children: Sequence[MetadataFilter] = (),
    ) -> None:
        self.operator = operator
        self.key_value = key_value
        self.children = children

    def __repr__(self):
        if self.children:
            return "\n".join(
                [
                    f"{self.operator.value}(",
                    *[
                        f"{textwrap.indent(repr(child), prefix=' ' * 2)},"
                        for child in self.children
                    ],
                    ")",
                ]
            )
        else:
            key, value = cast(tuple[str, str], self.key_value)
            return f"{self.operator.value}({key!r}, {value!r})"

    def to_json(self):
        return {
            self.operator.value: [child.to_json() for child in self.children]
            if self.children
            else dict([self.key_value])
        }

    @classmethod
    def from_json(cls, json: dict[str, Union[str, list[dict]]]) -> MetadataFilter:
        operator, value = next(iter(json.items()))

        operator = MetadataFilterOperator[operator.upper()]
        if isinstance(value, list):
            key_value = None
            children = [cls.from_json(child) for child in value]
        else:
            value = cast(dict[str, str], value)
            key_value = next(iter(value.items()))
            children = []

        return cls(operator, key_value=key_value, children=children)

    @staticmethod
    def _flatten(
        operator: MetadataFilterOperator, children: Sequence[MetadataFilter]
    ) -> list[MetadataFilter]:
        flat_children = []
        for child in children:
            if child.operator == operator:
                flat_children.extend(child.children)
            else:
                flat_children.append(child)
        return flat_children

    @classmethod
    def and_(cls, children: Sequence[MetadataFilter]) -> MetadataFilter:
        return cls(
            MetadataFilterOperator.AND,
            children=cls._flatten(MetadataFilterOperator.AND, children),
        )

    def __and__(self, other: Any) -> MetadataFilter:
        if not isinstance(other, MetadataFilter):
            return NotImplemented

        return self.and_([self, other])

    def __rand__(self, other: Any) -> MetadataFilter:
        return self.__and__(other)

    @classmethod
    def or_(cls, children: list[MetadataFilter]) -> MetadataFilter:
        return cls(
            MetadataFilterOperator.OR,
            children=cls._flatten(MetadataFilterOperator.OR, children),
        )

    def __or__(self, other: Any) -> MetadataFilter:
        if not isinstance(other, MetadataFilter):
            return NotImplemented

        return self.or_([self, other])

    def __ror__(self, other: Any) -> MetadataFilter:
        return self.__or__(other)

    @classmethod
    def eq(cls, key: str, value: str) -> MetadataFilter:
        return cls(MetadataFilterOperator.EQ, key_value=(key, value))


docs = ["doc1", "doc2", "doc2"]


# filter = MetadataFilter.or_([MetadataFilter.eq(doc) for doc in docs])
# print(filter)

filter = MetadataFilter.eq("tag", "a") | MetadataFilter.eq(
    "doc", "b"
) & MetadataFilter.eq("doc", "c")
# print(filter)

# print(json.dumps(filter.to_json(), indent=2))
print(MetadataFilter.from_json(filter.to_json()))


CHROMA = {
    MetadataFilterOperator.AND: "$and",
    MetadataFilterOperator.OR: "$or",
    MetadataFilterOperator.EQ: "$eq",
}


def chroma(filter):
    if filter.children:
        return {CHROMA[filter.operator]: [chroma(child) for child in filter.children]}
    else:
        key, value = cast(tuple[str, str], filter.key_value)
        return {key: {CHROMA[filter.operator]: value}}


print(chroma(filter))

import collections.abc


class Chat:
    def __init__(self, input, *, source_storage):
        if isinstance(input, MetadataFilter):
            documents = None
            metadata_filter = input
            prepared = True
        else:
            if isinstance(input, collections.abc.Collection):
                documents = input
            else:
                documents = [input]
            # to local document
            metadata_filter = MetadataFilter.or_(
                [MetadataFilter.eq("id", document.id) for document in documents]
            )
            prepared = False
        self.documents = documents
        self.metadata_filter = metadata_filter
        self.prepared = prepared

        # based on the value of prepared we should exclude SourceStorage.store from the
        # allowed params


class ChatPreparationConfiguration:
    def chat_data(self) -> tuple[Optional["documents"], "chatdata"]:
        # could we maybe do the upload here? that would simplify things quite a bit
        # if yes, we need to provide our file uploader widget as proper component and
        # not embedded into the UI
        # we also need the api wrapper here to be able to upload
        pass

    def __panel__(self):
        pass


class ChatInterogationConfiguration:
    def chat_data(self):
        pass

    def __panel__(self):
        pass
