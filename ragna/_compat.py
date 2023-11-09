import sys
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    Iterator,
    Mapping,
    Protocol,
    TypeVar,
)

if TYPE_CHECKING:
    if sys.version_info[:2] >= (3, 10):
        from importlib.metadata import EntryPoints
    else:
        from importlib_metadata import EntryPoints


__all__ = [
    "itertools_pairwise",
    "importlib_metadata_package_distributions",
    "importlib_metadata_entry_points",
]

T = TypeVar("T")


def _itertools_pairwise() -> Callable[[Iterable[T]], Iterator[tuple[T, T]]]:
    if sys.version_info[:2] >= (3, 10):
        from itertools import pairwise
    else:
        from itertools import tee
        from typing import Iterable, Iterator

        # https://docs.python.org/3/library/itertools.html#itertools.pairwise
        def pairwise(iterable: Iterable[T]) -> Iterator[tuple[T, T]]:
            # pairwise('ABCDEFG') --> AB BC CD DE EF FG
            a, b = tee(iterable)
            next(b, None)
            return zip(a, b)

    return pairwise


itertools_pairwise = _itertools_pairwise()


def _importlib_metadata_package_distributions() -> (
    Callable[[], Mapping[str, list[str]]]
):
    if sys.version_info[:2] >= (3, 10):
        from importlib.metadata import packages_distributions
    else:
        from importlib_metadata import packages_distributions

    return packages_distributions


importlib_metadata_package_distributions = _importlib_metadata_package_distributions()


class EntryPointsCallable(Protocol):
    def __call__(self, **kwargs: Any) -> "EntryPoints":
        ...


def _importlib_metadata_entry_points() -> EntryPointsCallable:
    if sys.version_info[:2] >= (3, 10):
        from importlib.metadata import entry_points
    else:
        from importlib_metadata import entry_points

    return entry_points


importlib_metadata_entry_points = _importlib_metadata_entry_points()
