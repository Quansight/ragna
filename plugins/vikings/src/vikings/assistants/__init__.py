__all__ = ["Ivar"]

from ragna.core import Assistant, Source


class Ivar(Assistant):
    """Ivar the Boneless"""

    @classmethod
    def display_name(cls) -> str:
        return "Ivar"

    @property
    def max_input_size(self) -> int:
        return 873

    def answer(self, prompt: str, sources: list[Source]) -> str:
        return "I am Ivar the Boneless! "
