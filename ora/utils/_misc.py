from itertools import chain, pairwise


def page_numbers_to_str(page_numbers: list[int]) -> str:
    if not page_numbers:
        return ""
    elif len(page_numbers) == 1:
        return str(page_numbers[0])

    ranges_str = []
    range_int = []
    for current_page_number, next_page_number in pairwise(
        chain(sorted(page_numbers), [None])
    ):
        range_int.append(current_page_number)
        if next_page_number is None or next_page_number > current_page_number + 1:
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
