"""
# Adding Source Storages

Ragna has builtin support for [several source storage types][ragna.source_storages], but there may be cases
where you want to use one that is not currently supported. 

This tutorial walks you through the basics of adding a source storage that is not currently supported. 
"""

# %%
# ## The Finished Product

# %%
# Here is the tutorial example printed in its entirety which will be explained below

from ragna.core import Source, SourceStorage
from ragna.core._document import Document


class tutorial_source_storage(SourceStorage):
    def __init__(self):
        # import database api

        # set up database
        ...

    def store(self, documents: list[Document]) -> None:
        """Store content of documents.

        Args:
            documents: Documents to store.
        """
        for document in documents:
            # store documents using database api
            ...

    def retrieve(self, documents: list[Document], prompt: str) -> list[Source]:
        """Retrieve sources for a given prompt.

        Args:
            documents: Documents to retrieve sources from.
            prompt: Prompt to retrieve sources for.

        Returns:
            Matching sources for the given prompt ordered by relevance.
        """
        return documents
