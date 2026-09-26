from clean_ia.analyzer.scanner import CODE_LANGUAGES
from clean_ia.index.chunker import chunk_file
from clean_ia.index.embeddings import TfidfIndex
from clean_ia.models import Chunk, ProjectReport


class CodeIndex:
    def __init__(self) -> None:
        self.chunks: list[Chunk] = []
        self._index = TfidfIndex()

    def build(self, report: ProjectReport) -> None:
        chunks: list[Chunk] = []
        for item in report.files:
            if item.language in CODE_LANGUAGES or item.language == "markdown":
                chunks.extend(chunk_file(item, report.root))
        self.chunks = chunks
        self._index.fit([chunk.text for chunk in chunks])

    def search(self, query: str, limit: int = 5) -> list[Chunk]:
        hits = self._index.search(query, limit)
        return [self.chunks[index] for index, _score in hits]
