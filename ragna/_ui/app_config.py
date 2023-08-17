import dataclasses
from pathlib import Path
from typing import Any

import panel as pn


@dataclasses.dataclass
class AppConfig:
    cache_root: Path = Path.home() / "ragna" / ".cache"

    def __post_init__(self):
        self.cache_root = self.cache_root.expanduser().resolve()
        self.cache_root.mkdir(parents=True, exist_ok=True)

    @property
    def user(self) -> str:
        return pn.state.user or "root"

    @property
    def user_info(self) -> dict[str, Any]:
        return pn.state.user_info or {}

    def browser_now(self):
        pass
