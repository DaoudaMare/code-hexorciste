import re
from pathlib import Path


def parse_styles(raw: str) -> frozenset[str]:
    text = raw.strip().lower().replace("hexagonal-tdd", "hexagonal,tdd").replace("hexa-tdd", "hexagonal,tdd")
    text = text.replace("+", ",").replace(" et ", ",")
    styles: set[str] = set()
    unknown: list[str] = []
    for part in text.split(","):
        token = part.strip()
        if not token:
            continue
        if token in {"hexa", "hexagonale", "hexagonal"}:
            styles.add("hexagonal")
        elif token == "tdd":
            styles.add("tdd")
        else:
            unknown.append(token)
    if not styles or unknown:
        names = ", ".join(unknown) or "vide"
        raise ValueError(f"Architecture inconnue : {names}. Choix : hexagonal, tdd, hexa-tdd.")
    return frozenset(styles)


def describe_styles(styles: frozenset[str]) -> str:
    lines = ["Refactorise le projet existant sans ajouter de fonctionnalité."]
    if "hexagonal" in styles:
        lines.append(
            "Hexagonale : place le métier dans domain, les cas d'usage dans application, "
            "les adaptateurs dans infrastructure et les entrées dans interfaces. "
            "Les ports, dont le repository, restent dans le domaine. Aucun framework dans le domaine."
        )
    if "tdd" in styles:
        lines.append(
            "TDD : pour chaque comportement déplacé, le test décrit le résultat attendu et passe. "
            "Adapte le test avant de déplacer le code. Les tests du domaine n'ouvrent ni base, ni réseau, ni fichier."
        )
    return "\n".join(lines)


def project_name(path: Path) -> str:
    raw = path.name.strip().lower().replace("-", "_").replace(" ", "_")
    cleaned = re.sub(r"[^a-z0-9_]", "_", raw)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"app_{cleaned}".strip("_")
    return cleaned or "app"


def ensure_empty(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(f"Le dossier n'est pas vide : {path}")
    path.mkdir(parents=True, exist_ok=True)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
