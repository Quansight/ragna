import hashlib
import json
from typing import Any


def compute_id(*input: Any) -> str:
    input = input if len(input) > 1 else input[0]
    if not isinstance(input, (str, bytes)):
        try:
            input = json.dumps(input)
        except TypeError:
            raise ValueError(
                f"Input can either be a bytes or str or something that is JSON "
                f"serializable, but got {input}."
            )
            raise
    if isinstance(input, str):
        input = input.encode()
    return hashlib.md5(input).hexdigest()
