import pytest
import ragna


@pytest.mark.parametrize(
    ("page_numbers", "expected"),
    [
        ([], ""),
        ([1], "1"),
        ([1, 2], "1, 2"),
        ([1, 2, 3], "1-3"),
        ([1, 2, 3, 5, 7, 8, 9], "1-3, 5, 7-9"),
    ],
)
def test_page_numbers_to_str(page_numbers, expected):
    assert ragna.utils.page_numbers_to_str(page_numbers) == expected
