import dataclasses
from pathlib import Path
from typing import Any

import panel as pn

from ragna._backend import ChatConfig, Llm, PageExtractor, SourceStorage


@dataclasses.dataclass
class AppComponents:
    page_extractors: dict[str, PageExtractor]
    source_storages: dict[str, SourceStorage]
    llms: dict[str, Llm]
    chat_configs: dict[str, ChatConfig]


@dataclasses.dataclass
class AppConfig:
    url: str
    port: int
    cache_root: Path

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
