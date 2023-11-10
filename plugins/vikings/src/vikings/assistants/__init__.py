__all__ = ["Ivar"]

from ragna.core import Assistant, Source


class IvarTheBoneless(Assistant):
    """Ivar the Boneless"""

    @classmethod
    def display_name(cls) -> str:
        return "Vikings/IvarTheBoneless"

    @property
    def max_input_size(self) -> int:
        return 873

    def answer(
        self, prompt: str, sources: list[Source], *, max_new_tokens: int = 256
    ) -> str:
        return "I am Ivar the Boneless! "
