from ragna.core import Document, Chunk, ChunkingModel

class NLTKChunkingModel(ChunkingModel):
    def __init__(self):
        super().__init__()

        # our text splitter goes here
        from langchain.text_splitter import NLTKTextSplitter
        self.text_splitter = NLTKTextSplitter()

    def chunk_documents(self, documents: list[Document]) -> list[Chunk]:
        # This is not perfect, but it's the only way I could get this to somewhat work
        chunks = []
        for document in documents:
            pages = list(document.extract_pages())
            text = "".join([page.text for page in pages])

            chunks += self.generate_chunks_from_text(self.text_splitter.split_text(text), document.id)

        return chunks
