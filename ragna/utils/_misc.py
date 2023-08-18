import itertools
from typing import Iterable, Iterator

from ragna._backend import Source


def page_numbers_to_str(page_numbers: list[int]) -> str:
    if not page_numbers:
        return ""
    elif len(page_numbers) == 1:
        return str(page_numbers[0])

    ranges_str = []
    range_int = []
    for current_page_number, next_page_number in itertools.pairwise(
        itertools.chain(sorted(page_numbers), [None])
    ):
        range_int.append(current_page_number)
        if (
            next_page_number is None
            or next_page_number > current_page_number + 1  # type: ignore[operator]
        ):
            match range_int:
                case [page]:
                    range_str = str(page)
                case [first_page, second_page]:
                    range_str = f"{first_page}, {second_page}"
                case [first_page, *_, last_page]:
                    range_str = f"{first_page}-{last_page}"
            ranges_str.append(range_str)
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
