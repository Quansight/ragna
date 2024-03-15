"""
# Adding Source Storages

Ragna has builtin support for [several source storage types][ragna.source_storages], but there may be cases
where you want to use one that is not currently supported. 

This tutorial walks you through the basics of adding a source storage that is not currently supported. 

!!! note

    This tutorial assumes that our `TutorialSourceStorage` class (shown below) is located in the file
    `ragna/source_storages/_tutorial.py`.
"""

# %%
# ## The Finished Product

# %%
# Here is the tutorial example printed in its entirety which will be explained below

# %%
# !!! note
#
#     The code snippet below only includes up to Step 1. To actually include your source storage
#     in Ragna, you must still perform Step 2.

from ragna.core import Source, SourceStorage


class TutorialSourceStorage(SourceStorage):
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
# !!! tip
#
#     For organizational purposes, this tutorial is divided into steps, but you may wish to perform
#     Step 2 during Step 1 for manual testing or debugging.

# %%
# ### Step 0: Import Source Storage Module and Write the Class Initializer

# %%
# Our source storage class will subclass the [`SourceStorage`][ragna.core.SourceStorage]
# abstract base class, so we import it. We also import [`Source`][ragna.core.Source]
# to use with the typing system.

# %%
# ```python
# from ragna.core import Source, SourceStorage
#
#
# class TutorialSourceStorage(SourceStorage):
#     def __init__(self):
#         # import database api
#
#         # set up database
#         ...
# ```

# %%
# ### Step 1: Implement Abstract Methods

# %%
# [`SourceStorage`][ragna.core.SourceStorage] has two abstract methods, [`store()`][ragna.core.SourceStorage.store] and [`retrieve()`][ragna.core.SourceStorage.retrieve].

# %%
# #### Step 1a: Implement [`store()`][ragna.core.SourceStorage.store]

# %%
# [`store()`][ragna.core.SourceStorage.store] takes a list of [`Source`][ragna.core.Source]s
# as an argument and places them in the database that you are using to hold them. This is
# different for each different source storage implementation.

# %%
# ```python
#     def store(self, sources: list[Source]) -> None:
#         """Store content of sources.
#
#         Args:
#             sources: Sources to store.
#         """
#         for document in sources:
#             # store sources using database api
#             ...
# ```

# %%
# #### Step 1b: Implement [`retrieve()`][ragna.core.SourceStorage.retrieve]

# %%
# [`retrieve()`][ragna.core.SourceStorage.retrieve] returns sources matching
# the given prompt in order of relevance.

# %%
# ```python
#     def retrieve(self, sources: list[Source], prompt: str) -> list[Source]:
#         """Retrieve sources for a given prompt.
#
#         Args:
#             sources: Sources to retrieve sources from.
#             prompt: Prompt to retrieve sources for.
#
#         Returns:
#             Matching sources for the given prompt ordered by relevance.
#         """
#         return sources
# ```

# %%
# ### Step 2: Include the Source Storage in Ragna

# %%
# Once you have created your source storage, you must add it to the system so that it
# is recognized. To do this, add your custom source storage to the `__all__` list in the file
# `ragna/source_storages/__init__.py`, and import it in the same file. An example is shown
# below.

# %%
# ```python
# __all__ = [
#     "Chroma",
#     "LanceDB",
#     "RagnaDemoSourceStorage",
#     "TutorialSourceStorage"
# ]
#
# from ._chroma import Chroma
# from ._demo import RagnaDemoSourceStorage
# from ._lancedb import LanceDB
# from ._tutorial import TutorialSourceStorage
#
# # [Rest of file...]
# ```

# %%
# !!! note
#     Although it is not a strict requirement, it is a convention that the items added to
#     `ragna/source_storages/__init__.py` appear in alphabetical order.
