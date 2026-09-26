from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ImportRef:
    module: str
    names: tuple[str, ...]
    lineno: int
    kind: str


@dataclass
class Symbol:
    name: str
    kind: str
    lineno: int
    end_lineno: int
    parent: str | None = None

    @property
    def qualified(self) -> str:
        return f"{self.parent}.{self.name}" if self.parent else self.name


@dataclass
class ParsedFile:
    path: Path
    language: str
    text: str
    lines: int
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[ImportRef] = field(default_factory=list)
    parse_error: str | None = None

    def relative(self, root: Path) -> str:
        return self.path.relative_to(root).as_posix()


@dataclass
class ExternalDependency:
    name: str
    source: str


@dataclass
class Smell:
    path: str
    line: int
    code: str
    message: str


@dataclass
class ProjectReport:
    root: Path
    files: list[ParsedFile]
    external: list[ExternalDependency]
    smells: list[Smell]
    cycles: list[tuple[str, ...]]

    @property
    def languages(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.files:
            counts[item.language] = counts.get(item.language, 0) + 1
        return counts


@dataclass
class Chunk:
    path: str
    symbol: str
    start: int
    end: int
    text: str


@dataclass
class FileChange:
    path: str
    diff: str
    applied: bool


@dataclass
class RunLog:
    architecture: dict | None = None
    changes: list[FileChange] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class AgentResult:
    text: str
    log: RunLog


@dataclass(frozen=True)
class AuditFinding:
    path: str
    line: int
    code: str
    severity: str
    message: str
    recommendation: str


@dataclass
class AuditReport:
    kind: str
    root: Path
    file_count: int
    findings: list[AuditFinding]
