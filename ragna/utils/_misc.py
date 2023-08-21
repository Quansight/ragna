import itertools
from typing import Iterable, Iterator

from ragna._backend import Source

from ragna._compat import itertools_pairwise


def page_numbers_to_str(page_numbers: list[int]) -> str:
    if not page_numbers:
        return ""
    elif len(page_numbers) == 1:
        return str(page_numbers[0])

    ranges_str = []
    range_int = []
    for current_page_number, next_page_number in itertools_pairwise(
        itertools.chain(sorted(page_numbers), [None])
    ):
        range_int.append(current_page_number)
        if (
            next_page_number is None
            or next_page_number > current_page_number + 1  # type: ignore[operator]
        ):
            ranges_str.append(
                ", ".join(map(str, range_int))
                if len(range_int) < 3
                else f"{range_int[0]}-{range_int[-1]}"
            )
            range_int = []

    return ", ".join(ranges_str)


def take_sources_up_to_max_tokens(
    sources: Iterable[Source], *, max_tokens: int
) -> Iterator[Source]:
    total = 0
    for source in sources:
        new_total = total + source.num_tokens
        if new_total > max_tokens:
            break

        yield source
        total = new_total
