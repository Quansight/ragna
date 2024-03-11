from abc import ABC, abstractmethod

import tiktoken

from ragna.core import (
    Document,
)
from ragna.source_storages._vector_database import Chunk

from ragna.core._components import Component, Document

class GenericChunkingModel(Component, ABC):
    def __init__(self):
        # we need a way of estimating tokens that is common to all chunking models
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    @abstractmethod
    def chunk_documents(self, documents: list[Document]) -> list[Chunk]:
        raise NotImplementedError


class NLTKChunkingModel(GenericChunkingModel):
    def __init__(self):
        super().__init__()

        # our text splitter goes here
        from langchain.text_splitter import NLTKTextSplitter
        self.text_splitter = NLTKTextSplitter()

    def chunk_documents(self, documents: list[Document]) -> list[Chunk]:
        # Problem: chunk need to preserve its page number
        chunks = []
        for document in documents:
            for page in document.extract_pages():
                chunks_raw = self.text_splitter.split_text(page.text)
                chunks += [Chunk(page_numbers=[page.number], text=chunk, document_id=document.id, num_tokens=len(self.tokenizer.encode(chunk))) for chunk in chunks_raw]
        return chunks
