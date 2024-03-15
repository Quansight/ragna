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


class tutorial_source_storage(SourceStorage):
    def __init__(self):
        # import database api

        # set up database
        ...

    def store(self, sources: list[Source]) -> None:
        """Store content of sources.

        Args:
            sources: Sources to store.
        """
        for document in sources:
            # store sources using database api
            ...

    def retrieve(self, sources: list[Source], prompt: str) -> list[Source]:
        """Retrieve sources for a given prompt.

        Args:
            sources: Sources to retrieve sources from.
            prompt: Prompt to retrieve sources for.

        Returns:
            Matching sources for the given prompt ordered by relevance.
        """
        return sources


# %%
# ## The Explanation

# %%
# ### Step 0: Import source storage module and write the class initializer

# %%
# Our source storage class will subclass the [`SourceStorage`][ragna.core.SourceStorage]
# abstract base class, so we import it. We also import [`Source`][ragna.core.Source]
# to use with the typing system.

# %%
# ```python
# from ragna.core import Source, SourceStorage
#
#
# class tutorial_source_storage(SourceStorage):
#     def __init__(self):
#         # import database api
#
#         # set up database
#         ...
# ```
