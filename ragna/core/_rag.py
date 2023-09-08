import importlib.util
import itertools
from pathlib import Path

from types import ModuleType
from typing import Iterable

from pluggy import PluginManager

import ragna._backend


class Chat:
    def __init__(self, *documents, source_storage, llm, start, **chat_params):
        self.documents = documents
        self.source_storage = source_storage
        self.llm = llm
        self.chat_params = chat_params

        if start:
            self.source_storage.store(documents, **chat_params)

    def answer(self, prompt):
        sources = self.source_storage.retrieve(prompt, **self.chat_params)
        return self.llm.complete(prompt, sources, **self.chat_params)


class Rag:
    _page_extractors: dict
    _source_storages: dict
    _llms: dict

    def __init__(
        self,
        *extensions: str,
        additional_hookspecs: Iterable[ModuleType],
        no_deselect: bool = False,
    ):
        self._plugin_manager = self._register_extensions(
            extensions, additional_hookspecs
        )

        for specname, components in self._load_components(
            no_deselect=no_deselect
        ).items():
            # ragna_llm -> _llms
            name = f"{specname.removeprefix('ragna')}s"
            setattr(self, name, components)

    def _register_extensions(self, extensions, additional_hookspecs) -> PluginManager:
        plugin_manager = PluginManager("ragna")

        for hookspec in itertools.chain(
            [ragna._backend.hookspecs], additional_hookspecs
        ):
            plugin_manager.add_hookspecs(hookspec)

        for extension in extensions:
            plugin_manager.register(self._load_extension(extension))

        return plugin_manager

    def _load_extension(self, source: str) -> ModuleType:
        path = Path(source).expanduser().resolve()
        if path.exists():
            spec = importlib.util.spec_from_file_location(path.name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:
            module = importlib.import_module(source)

        return module

    def _load_components(self, *, no_deselect):
        components = {
            specname: {}
            for specname in [
                "ragna_page_extractor",
                "ragna_source_storage",
                "ragna_llm",
            ]
        }
        deselected = []
        for specname in components:
            for component_cls in getattr(self._plugin_manager.hook, specname)():
                name = component_cls.display_name()
                if not component_cls.is_available():
                    deselected.append(name)
                    continue

                components[specname][name] = component_cls()

        if no_deselect and deselected:
            # FIXME: make this a custom error that can be excepted by the CLI
            raise RuntimeError(str(deselected))

        no_components = [
            specname
            for specname, available_components in components.items()
            if not available_components
        ]
        if no_components:
            # FIXME: make this a custom error that can be excepted by the CLI
            raise RuntimeError(str(no_components))

        return components

    def start_chat(self, *documents, **chat_params):
        # FIXME We need proper validation here
        source_storage_name = chat_params["source_storage_name"]
        llm_name = chat_params["llm_name"]
        return Chat(
            *documents,
            source_storage=self._source_storages[source_storage_name],
            llm=self._llms[llm_name],
            **chat_params,
        )

    def answer(self, prompt: str, chat_id: str) -> str:
        chat = self._chats[chat_id]
        return chat.answer(prompt)
