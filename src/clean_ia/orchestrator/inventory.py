import shutil
import subprocess
from pathlib import Path

from clean_ia.models import ProjectReport
from clean_ia.orchestrator.mermaid_ext import APP_CLI

SKIP_NAMES = {"main", "setUp", "tearDown"}


def render_inventory(report: ProjectReport) -> str:
    packages = _packages(report)
    extensions = _extensions()
    unused = _unused_symbols(report)
    return "\n".join(
        [
            "Packages installés. Ne les retire qu'après un oui explicite :",
            _lines(packages),
            "",
            "Extensions installées. Ne les retire qu'après un oui explicite :",
            _lines(extensions),
            "",
            "Méthodes et fonctions sans autre référence dans le projet :",
            _lines(unused),
        ]
    )


def _packages(report: ProjectReport) -> list[str]:
    return [f"{dep.name} ({dep.source})" for dep in report.external]


def _unused_symbols(report: ProjectReport) -> list[str]:
    corpus = "\n".join(item.text for item in report.files)
    found: list[str] = []
    for item in report.files:
        if item.language != "python":
            continue
        for symbol in item.symbols:
            if symbol.kind not in {"function", "method"}:
                continue
            if symbol.name.startswith("_") or symbol.name in SKIP_NAMES or symbol.name.startswith("test"):
                continue
            if corpus.count(symbol.name) <= 1:
                found.append(f"{item.relative(report.root)}:{symbol.qualified}")
    return found


def _extensions() -> list[str]:
    binary = APP_CLI if APP_CLI.is_file() else None
    if binary is None:
        found = shutil.which("cursor")
        binary = Path(found) if found else None
    if binary is None:
        return []
    try:
        completed = subprocess.run(
            [str(binary), "--list-extensions"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _lines(items: list[str]) -> str:
    if not items:
        return "- aucun détecté"
    return "\n".join(f"- {item}" for item in items)
