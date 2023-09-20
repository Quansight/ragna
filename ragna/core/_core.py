from __future__ import annotations

import uuid as uuid_


class RagnaException(Exception):
    # The values below are sentinels to be used with the http_detail field.
    # This tells the API to use the event as detail
    EVENT = object()
    # This tells the API to use the error message as detail
    MESSAGE = object()

    def __init__(self, event="", http_status_code=500, http_detail=None, **extra):
        # FIXME: remove default value for event
        self.event = event
        self.http_status_code = http_status_code
        self.http_detail = http_detail
        self.extra = extra

    def __repr__(self):
        return ", ".join([self.event, *[f"{k}={v}" for k, v in self.extra.items()]])


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
