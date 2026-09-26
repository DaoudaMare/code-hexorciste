from pathlib import Path

from clean_ia.analyzer.dependencies import collect_external, find_cycles, local_import_graph
from clean_ia.analyzer.parser import parse_file
from clean_ia.analyzer.scanner import iter_source_files
from clean_ia.analyzer.smells import detect_smells
from clean_ia.models import ProjectReport


class ProjectAnalyzer:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def analyze(self) -> ProjectReport:
        if not self.root.is_dir():
            raise FileNotFoundError(f"Dossier introuvable : {self.root}")
        files = []
        for path in iter_source_files(self.root):
            parsed = parse_file(path)
            if parsed is not None:
                files.append(parsed)
        graph = local_import_graph(self.root, files)
        return ProjectReport(
            root=self.root,
            files=files,
            external=collect_external(self.root),
            smells=detect_smells(self.root, files),
            cycles=find_cycles(graph),
        )


def render_report(report: ProjectReport, limit: int = 80) -> str:
    langs = ", ".join(f"{name}: {count}" for name, count in sorted(report.languages.items()))
    lines = [
        f"Projet : {report.root}",
        f"Fichiers : {len(report.files)}" + (f" ({langs})" if langs else ""),
    ]
    if report.external:
        names = ", ".join(dep.name for dep in report.external[:30])
        lines.append(f"Dépendances : {names}")
    if report.cycles:
        lines.append("Imports circulaires :")
        for cycle in report.cycles[:10]:
            lines.append("  " + " -> ".join(cycle))
    if report.smells:
        lines.append(f"Problèmes ({len(report.smells)}) :")
        for smell in report.smells[:limit]:
            lines.append(f"  {smell.path}:{smell.line} [{smell.code}] {smell.message}")
    else:
        lines.append("Aucun problème structurel évident.")
    lines.append("Arborescence :")
    lines.extend(_tree(report))
    return "\n".join(lines)


def _tree(report: ProjectReport, limit: int = 150) -> list[str]:
    rows = [item.relative(report.root) for item in report.files]
    shown = rows[:limit]
    extra = len(rows) - len(shown)
    rendered = [f"  {row}" for row in shown]
    if extra > 0:
        rendered.append(f"  … {extra} fichiers de plus")
    return rendered
