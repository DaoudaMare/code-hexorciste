import hashlib
from pathlib import Path

from clean_ia.models import ProjectReport


def suggest_architecture(report: ProjectReport) -> dict:
    python_files = any(item.language == "python" for item in report.files)
    layers = _python_layers() if python_files else _generic_layers()
    steps = _steps(report.cycles, python_files)
    summary = (
        f"{len(report.files)} fichiers, {len(report.smells)} problèmes structurels, "
        f"{len(report.cycles)} cycles d'import."
    )
    return {"name": "Architecture hexagonale", "summary": summary, "layers": layers, "steps": steps}


def _layer(name: str, responsibility: str, path: str) -> dict:
    return {"name": name, "responsibility": responsibility, "target_paths": [path]}


def _python_layers() -> list[dict]:
    return [
        _layer("domain", "Entités, règles métier et ports, dont le repository.", "src/<package>/domain"),
        _layer("application", "Cas d'usage. Ils dépendent des ports, pas des adaptateurs.", "src/<package>/application"),
        _layer("infrastructure", "Adaptateurs sortants : repository concret, fichiers, API.", "src/<package>/infrastructure"),
        _layer("interfaces", "Adaptateurs entrants : CLI, HTTP.", "src/<package>/interfaces"),
    ]


def _generic_layers() -> list[dict]:
    return [
        _layer("domain", "Métier et ports, dont le repository.", "src/domain"),
        _layer("application", "Cas d'usage testés sans infrastructure.", "src/application"),
        _layer("adapters", "Adaptateurs entrants et sortants.", "src/adapters"),
    ]


def _steps(cycles: list, python_files: bool) -> list[str]:
    steps = [
        "Placer les ports, dont le repository, dans le domaine.",
        "Écrire d'abord les tests de cas d'usage, sans base ni framework.",
        "Garder une seule raison de changer par module.",
        "Implémenter les adaptateurs dans l'infrastructure et les interfaces.",
    ]
    if not python_files:
        steps = ["Séparer la logique, les adaptateurs et l'interface.", *steps[:2]]
    if cycles:
        steps.insert(0, "Casser les imports circulaires avant de déplacer les modules.")
    return steps


def format_architecture(plan: dict) -> str:
    lines = [plan.get("name", "Architecture"), "", plan.get("summary", ""), "", "Couches :"]
    for layer in plan.get("layers", []):
        paths = ", ".join(layer.get("target_paths", []))
        lines.append(f"- {layer.get('name')} : {layer.get('responsibility')} [{paths}]")
    lines.append("")
    lines.append("Étapes :")
    for index, step in enumerate(plan.get("steps", []), start=1):
        lines.append(f"{index}. {step}")
    return "\n".join(lines)


def cache_dir(root: Path) -> Path:
    digest = hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:16]
    path = Path.home() / ".cache" / "clean_ia" / digest
    path.mkdir(parents=True, exist_ok=True)
    return path
