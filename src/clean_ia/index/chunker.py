from clean_ia.models import Chunk, ParsedFile

WINDOW = 80
OVERLAP = 15
MAX_CHUNK_CHARS = 6000


def chunk_file(source: ParsedFile, root) -> list[Chunk]:
    rel = source.relative(root)
    if source.language not in {"python", "javascript", "typescript"} or not source.symbols:
        return _windows(rel, source.text)
    file_lines = source.text.splitlines()
    chunks: list[Chunk] = []
    for symbol in source.symbols:
        start = max(symbol.lineno, 1)
        end = max(symbol.end_lineno, start)
        body = "\n".join(file_lines[start - 1 : end])
        header = f"# file: {rel}\n# symbol: {symbol.qualified}\n"
        chunks.append(
            Chunk(
                path=rel,
                symbol=symbol.qualified,
                start=start,
                end=end,
                text=(header + body)[:MAX_CHUNK_CHARS],
            )
        )
    return chunks or _windows(rel, source.text)


def _windows(path: str, text: str) -> list[Chunk]:
    rows = text.splitlines()
    if not rows:
        return []
    chunks: list[Chunk] = []
    start = 0
    while start < len(rows):
        end = min(start + WINDOW, len(rows))
        body = "\n".join(rows[start:end])
        chunks.append(
            Chunk(
                path=path,
                symbol=f"lines:{start + 1}-{end}",
                start=start + 1,
                end=end,
                text=f"# file: {path}\n{body}"[:MAX_CHUNK_CHARS],
            )
        )
        if end == len(rows):
            break
        start = end - OVERLAP
    return chunks
