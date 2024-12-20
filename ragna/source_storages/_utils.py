from typing import NoReturn

from fastapi import status

from ragna.core import RagnaException, SourceStorage


def raise_no_corpuses_available(source_storage: SourceStorage) -> NoReturn:
    __tracebackhide__ = True
    raise RagnaException(
        "No corpuses available",
        source_storage=str(source_storage),
        http_status_code=status.HTTP_400_BAD_REQUEST,
        http_detail=RagnaException.MESSAGE,
    ) from None


def raise_non_existing_corpus(
    source_storage: SourceStorage, corpus_name: str
) -> NoReturn:
    __tracebackhide__ = True
    raise RagnaException(
        "Corpus does not exist",
        source_storage=str(source_storage),
        corpus_name=corpus_name,
        http_status_code=status.HTTP_400_BAD_REQUEST,
        http_detail=RagnaException.MESSAGE,
    ) from None
