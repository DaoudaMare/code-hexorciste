import os
from pathlib import Path

IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    "dist",
    "build",
    "target",
    "coverage",
    ".clean_ia",
}
MAX_FILE_BYTES = 500_000

LANG_BY_SUFFIX = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".c": "c",
    ".h": "c",
    ".swift": "swift",
    ".json": "json",
    ".toml": "toml",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".md": "markdown",
    ".html": "html",
    ".css": "css",
    ".sql": "sql",
}

CODE_LANGUAGES = {
    "python",
    "javascript",
    "typescript",
    "go",
    "rust",
    "java",
    "kotlin",
    "ruby",
    "php",
    "csharp",
    "cpp",
    "c",
    "swift",
    "sql",
}


def iter_source_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in IGNORE_DIRS and not name.startswith("."))
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if path.suffix.lower() not in LANG_BY_SUFFIX:
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield path


def language_of(path: Path) -> str:
    return LANG_BY_SUFFIX.get(path.suffix.lower(), "text")


def read_text(path: Path) -> str | None:
    data = path.read_bytes()
    if b"\0" in data:
        return None
    return data.decode("utf-8", errors="replace")
