import builtins
import sys
from typing import (
    AsyncIterator,
    Awaitable,
    Callable,
    Iterable,
    Iterator,
    Mapping,
    TypeVar,
)

__all__ = ["itertools_pairwise", "importlib_metadata_package_distributions", "anext"]

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


def _anext() -> Callable[[AsyncIterator[T]], Awaitable[T]]:
    if sys.version_info[:2] >= (3, 10):
        anext = builtins.anext
    else:
        sentinel = object()

        def anext(
            ait: AsyncIterator[T],
            default: T = sentinel,  # type: ignore[assignment]
        ) -> Awaitable[T]:
            async def anext_impl() -> T:
                try:
                    return await ait.__anext__()
                except StopAsyncIteration:
                    if default is not sentinel:
                        return default

                    raise

            return anext_impl()

    return anext


anext = _anext()
