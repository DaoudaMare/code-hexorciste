from pathlib import Path

MODEL_FILE = "modelisation.md"
EXPLAIN_FILE = "explication.md"


def ensure_architecture_docs(root: Path, plan: dict, narrative: str = "") -> Path:
    folder = root / "architecture"
    folder.mkdir(parents=True, exist_ok=True)
    model = folder / MODEL_FILE
    explain = folder / EXPLAIN_FILE
    if not model.is_file():
        model.write_text(_model(plan), encoding="utf-8")
    if not explain.is_file():
        explain.write_text(_explain(plan, narrative), encoding="utf-8")
    return folder


def _model(plan: dict) -> str:
    layers = plan.get("layers") or []
    names = [layer.get("name") or "couche" for layer in layers]
    lines = ["# Modélisation", "", "```mermaid", "flowchart TB"]
    center = "domain" if "domain" in names else (names[0] if names else "domain")
    lines.append(f"  {_node(center)}[{center}]")
    for name in names:
        if name == center:
            continue
        lines.append(f"  {_node(name)}[{name}]")
        lines.append(f"  {_node(name)} --> {_node(center)}")
    lines.extend(["```", "", "## Couches", ""])
    for layer in layers:
        paths = ", ".join(layer.get("target_paths") or [])
        lines.append(f"- **{layer.get('name')}** : {layer.get('responsibility')} ({paths})")
    lines.append("")
    return "\n".join(lines)


def _explain(plan: dict, narrative: str) -> str:
    summary = plan.get("summary") or "Le projet a besoin de frontières plus nettes."
    steps = plan.get("steps") or []
    advantages = [
        "Le domaine ne connaît ni le framework, ni SQL, ni le disque.",
        "Le repository se remplace dans les tests par un double en mémoire.",
        "SOLID limite la taille des ports et les raisons de changer.",
        "Le TDD protège les cas d'usage avant le déplacement du code.",
    ]
    drawbacks = [
        "Plus de fichiers : port, adaptateur et tests pour chaque repository.",
        "La discipline TDD ralentit le premier découpage.",
        "Un port trop large casse le principe de ségrégation d'interface.",
    ]
    if "circul" in " ".join(steps).lower():
        drawbacks.append("Les imports circulaires doivent être cassés avant le déplacement.")
    lines = [
        "# Explication",
        "",
        f"## Pourquoi",
        "",
        summary,
        "",
        "Ce découpage place le métier au centre, les repositories derrière un port, et les tests devant le code.",
        "",
        "## Avantages",
        "",
    ]
    lines.extend(f"- {item}" for item in advantages)
    lines.extend(["", "## Inconvénients", ""])
    lines.extend(f"- {item}" for item in drawbacks)
    if narrative.strip():
        lines.extend(["", "## Détail de l'agent", "", narrative.strip()])
    lines.append("")
    return "\n".join(lines)


def _node(name: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in name)
