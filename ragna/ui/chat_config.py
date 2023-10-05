from typing import Any

import panel as pn
import param

# @dataclasses.dataclass
# class AppComponents:
#     page_extractors: dict[str, PageExtractor]
#     source_storages: dict[str, SourceStorage]
#     llms: dict[str, Llm]


class ChatConfig(param.Parameterized):
    source_storage_name = param.Selector()
    llm_name = param.Selector()
    extra = param.Dict(default={})
    # components = param.ClassSelector(AppComponents)

    def __init__(
        self,
        *,
        # components,
        source_storage_names,
        llm_names,
        extra,
    ):
        super().__init__(
            extra=extra,
        )
        self.param.source_storage_name.objects = source_storage_names
        self.source_storage_name = source_storage_names[0]
        self.param.llm_name.objects = llm_names
        self.llm_name = llm_names[0]

    def __panel__(self):
        """Could be left empty to provide no input from users"""
        return pn.Column(
            pn.widgets.Select.from_param(self.param.source_storage_name),
            pn.widgets.Select.from_param(self.param.llm_name),
        )

    def get_config(self) -> tuple[str, str, dict[str, Any]]:
        return {
            "source_storage_name": self.source_storage_name,
            "llm_name": self.llm_name,
            "extra": {},
        }

    def __repr__(self) -> str:
        return "DemoConfig"
