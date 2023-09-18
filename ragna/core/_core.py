from __future__ import annotations

import uuid as uuid_


class RagnaException(Exception):
    pass


class RagnaId(uuid_.UUID):
    @classmethod
    def from_uuid(cls, uuid: uuid_.UUID) -> RagnaId:
        return cls(int=uuid.int)

    @classmethod
    def is_valid_str(cls):
        pass

    @staticmethod
    def make():
        return RagnaId.from_uuid(uuid_.uuid4())
