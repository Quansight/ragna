import sys


__all__ = ["itertools_pairwise", "importlib_metadata_package_distributions"]


def _itertools_pairwise():
    if sys.version_info[:2] >= (3, 10):
        from itertools import pairwise
    else:
        from itertools import tee
        from typing import Iterable, Iterator, TypeVar

        T = TypeVar("T")

        # https://docs.python.org/3/library/itertools.html#itertools.pairwise
        def pairwise(iterable: Iterable[T]) -> Iterator[tuple[T, T]]:
            # pairwise('ABCDEFG') --> AB BC CD DE EF FG
            a, b = tee(iterable)
            next(b, None)
            return zip(a, b)

    return pairwise


itertools_pairwise = _itertools_pairwise()


def _importlib_metadata_package_distributions():
    if sys.version_info[:2] >= (3, 10):
        from importlib.metadata import packages_distributions
    else:
        from importlib_metadata import packages_distributions

    return packages_distributions


importlib_metadata_package_distributions = _importlib_metadata_package_distributions()
