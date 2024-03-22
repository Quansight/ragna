from ragna.core import (
    PackageRequirement,
    Requirement,
    SourceStorage,
)

class VectorDatabaseSourceStorage(SourceStorage):
    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [
            # This looks like this should only be a requirement for Chroma, but it is
            # not. Chroma solved one major UX painpoint of vector DBs: the need for an
            # embedding function. Normally, one would pull in a massive amount
            # (in numbers as well as in size) of transitive dependencies that are hard
            # to manage and mostly not even used by the vector DB. Chroma provides a
            # wrapper around a compiled embedding function that has only minimal
            # requirements. We use this as base for all of our Vector DBs.
            PackageRequirement("chromadb>=0.4.13"),
            PackageRequirement("tiktoken"),
        ]