from typing import Any

import panel as pn

from ragna.extensions import ChatConfig, hookimpl


class DefaultChatConfig(ChatConfig):
    source_storage_name = "test"
    llm_name = "test"

    def __init__(self, app_config):
        pass

    def __panel__(self):
        return pn.Column(
            pn.pane.Markdown("Hello"),
            pn.pane.Markdown("Goodbye"),
            # pn.widgets.Select.from_param(self.param.source_storage_name),
            # pn.widgets.Select.from_param(self.param.llm_name),
        )

    def get_config(self) -> tuple[str, str, dict[str, Any]]:
        return self.source_storage_name, self.llm_name, {}


@hookimpl(specname="ragna_chat_config")
def chat_config():
    return DefaultChatConfig
