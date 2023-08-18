from typing import Any

import param

from ragna._backend import DocumentMetadata, Llm, SourceStorage


class ChatConfig(param.Parameterized):
    llm = param.ClassSelector(Llm)
    source_storage = param.ClassSelector(SourceStorage)
    document_metadatas = param.List(item_type=DocumentMetadata)
    chat_log = param.List(item_type=str)
    extra = param.Dict()

    def __init__(
        self,
        llm: Llm,
        source_storage: SourceStorage,
        document_metadatas: list[DocumentMetadata],
        **extra: Any
    ):
        super().__init__(
            llm=llm,
            source_storage=source_storage,
            document_metadatas=document_metadatas,
            extra=extra,
        )
