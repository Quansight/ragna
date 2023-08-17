import pytest
from ragna._backend import compute_id


class TestComputeId:
    @pytest.mark.parametrize(
        "input",
        [
            (b"foo",),
            ("foo",),
            (["foo", "bar"],),
            ("foo", ["bar", "baz"]),
        ],
    )
    def test_smoke(self, input):
        assert isinstance(compute_id(*input), str)

    @pytest.mark.parametrize(
        "input",
        [
            ([b"foo"],),
            (object(),),
        ],
    )
    def test_error(self, input):
        with pytest.raises(ValueError):
            compute_id(*input)
