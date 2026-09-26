import difflib
import json
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from clean_ia.index.store import CodeIndex
from clean_ia.models import FileChange, RunLog

OUTPUT_LIMIT = 12_000
READ_LINE_LIMIT = 400
PROTECTED = {".env", ".env.local", "credentials.json", "id_rsa"}
TEST_BINARIES = {"pytest", "python", "python3", "npm", "pnpm", "yarn", "go", "cargo", "uv", "make"}


@dataclass
class ToolContext:
    root: Path
    log: RunLog
    index: CodeIndex
    apply: bool
    writes_enabled: bool


def tool_schemas() -> list[dict]:
    return [
        *_file_schemas(),
        _schema(
            "run_tests",
            "Lance les tests du projet. La commande est une liste, sans shell.",
            {"command": {"type": "array", "items": {"type": "string"}}},
            [],
        ),
        _schema("git_diff", "Montre le statut git et le diff du projet.", {"path": {"type": "string"}}, []),
        _schema(
            "search_code",
            "Recherche les extraits de code les plus proches d'une question.",
            {"query": {"type": "string"}, "limit": {"type": "integer"}},
            ["query"],
        ),
        _schema(
            "submit_architecture",
            "Enregistre l'architecture cible avant toute modification.",
            {
                "name": {"type": "string"},
                "summary": {"type": "string"},
                "layers": {"type": "array", "items": {"type": "object"}},
                "steps": {"type": "array", "items": {"type": "string"}},
            },
            ["name", "summary", "layers", "steps"],
        ),
    ]


def _file_schemas() -> list[dict]:
    return [
        _schema(
            "list_directory",
            "Liste le contenu d'un dossier du projet.",
            {"path": {"type": "string", "description": "Chemin relatif. Vide pour la racine."}},
            [],
        ),
        _schema(
            "read_file",
            "Lit un fichier du projet, éventuellement une plage de lignes.",
            {"path": {"type": "string"}, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}},
            ["path"],
        ),
        _schema(
            "write_file",
            "Écrit un fichier complet. En mode plan, renvoie seulement le diff.",
            {"path": {"type": "string"}, "content": {"type": "string"}},
            ["path", "content"],
        ),
    ]


def execute(name: str, arguments: dict, context: ToolContext) -> str:
    handlers = {
        "list_directory": _list_directory,
        "read_file": _read_file,
        "write_file": _write_file,
        "run_tests": _run_tests,
        "git_diff": _git_diff,
        "search_code": _search_code,
        "submit_architecture": _submit_architecture,
    }
    handler = handlers.get(name)
    if handler is None:
        return f"Outil inconnu : {name}"
    try:
        return _clip(handler(arguments, context))
    except Exception as exc:
        return f"Erreur {name} : {exc}"


def _schema(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "name": name,
        "description": description,
        "input_schema": {"type": "object", "properties": properties, "required": required},
    }


def _clip(text: str) -> str:
    if len(text) <= OUTPUT_LIMIT:
        return text
    return text[:OUTPUT_LIMIT] + "\n… sortie tronquée"


def _resolve(root: Path, raw: str) -> Path:
    root = root.resolve()
    relative = Path(raw or ".")
    if relative.is_absolute():
        raise ValueError("Le chemin doit être relatif au projet.")
    path = (root / relative).resolve()
    if path != root and root not in path.parents:
        raise ValueError("Chemin hors du projet.")
    return path


def _guard(path: Path) -> None:
    if path.name in PROTECTED or path.suffix in {".pem", ".key"}:
        raise ValueError("Fichier sensible, écriture refusée.")
    if ".git" in path.parts:
        raise ValueError("Écriture dans .git refusée.")


def _list_directory(arguments: dict, context: ToolContext) -> str:
    path = _resolve(context.root, arguments.get("path") or ".")
    if not path.is_dir():
        return "Dossier introuvable."
    entries = []
    for child in sorted(path.iterdir(), key=lambda item: item.name)[:200]:
        if child.name.startswith("."):
            continue
        suffix = "/" if child.is_dir() else ""
        entries.append(child.name + suffix)
    return "\n".join(entries) or "(vide)"


def _read_file(arguments: dict, context: ToolContext) -> str:
    path = _resolve(context.root, arguments["path"])
    if not path.is_file():
        return "Fichier introuvable."
    rows = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = max(int(arguments.get("start_line") or 1), 1)
    end = int(arguments.get("end_line") or min(len(rows), start + READ_LINE_LIMIT - 1))
    end = min(end, start + READ_LINE_LIMIT - 1, len(rows))
    body = "\n".join(f"{number}|{rows[number - 1]}" for number in range(start, end + 1))
    note = "" if end == len(rows) else f"\n… lignes {end + 1}-{len(rows)} non lues"
    return body + note


def _write_file(arguments: dict, context: ToolContext) -> str:
    if not context.writes_enabled:
        return "Écriture désactivée dans ce mode. Décris le plan sans modifier les fichiers."
    path = _resolve(context.root, arguments["path"])
    _guard(path)
    content = arguments.get("content")
    if not isinstance(content, str):
        return "content doit être une chaîne."
    previous = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    if previous == content:
        return "Aucun changement."
    diff = "".join(
        difflib.unified_diff(
            previous.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=arguments["path"],
            tofile=arguments["path"],
        )
    )
    applied = False
    if context.apply:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        applied = True
    rel = path.relative_to(context.root.resolve()).as_posix()
    context.log.changes.append(FileChange(path=rel, diff=diff or rel, applied=applied))
    status = "écrit" if applied else "proposé"
    return f"Fichier {status} : {rel}\n{diff[:4000]}"


def _run_tests(arguments: dict, context: ToolContext) -> str:
    command = arguments.get("command") or _default_test_command(context.root)
    if not command:
        return "Aucun lanceur de tests détecté."
    if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
        return "command doit être une liste de chaînes."
    binary = Path(command[0]).name
    if binary not in TEST_BINARIES:
        return f"Commande refusée : {binary}"
    if any(any(char in part for char in "|&;<>`$") for part in command):
        return "Métacaractères shell refusés."
    completed = subprocess.run(
        command,
        cwd=context.root,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    output = (completed.stdout + "\n" + completed.stderr).strip()
    context.log.notes.append(f"tests {shlex.join(command)} -> {completed.returncode}")
    return f"code {completed.returncode}\n{output}"


def _default_test_command(root: Path) -> list[str] | None:
    if (root / "pytest.ini").is_file() or (root / "tests").is_dir():
        return ["python3", "-m", "pytest", "-q"]
    if (root / "package.json").is_file():
        return ["npm", "test"]
    if (root / "go.mod").is_file():
        return ["go", "test", "./..."]
    if (root / "Cargo.toml").is_file():
        return ["cargo", "test"]
    return None


def _git_diff(arguments: dict, context: ToolContext) -> str:
    if not (context.root / ".git").exists():
        return "Pas un dépôt git."
    args = ["git", "status", "--short"]
    if arguments.get("path"):
        args.append("--")
        args.append(arguments["path"])
    status = _git(args, context.root)
    diff_args = ["git", "diff", "--", arguments["path"]] if arguments.get("path") else ["git", "diff"]
    diff = _git(diff_args, context.root)
    return f"{status}\n\n{diff}".strip()


def _git(args: list[str], root: Path) -> str:
    completed = subprocess.run(args, cwd=root, capture_output=True, text=True, timeout=30, check=False)
    return (completed.stdout or completed.stderr).strip()


def _search_code(arguments: dict, context: ToolContext) -> str:
    limit = int(arguments.get("limit") or 5)
    chunks = context.index.search(arguments.get("query") or "", max(1, min(limit, 10)))
    if not chunks:
        return "Aucun extrait."
    parts = [f"{chunk.path}:{chunk.start} {chunk.symbol}\n{chunk.text[:1500]}" for chunk in chunks]
    return "\n\n".join(parts)


def _submit_architecture(arguments: dict, context: ToolContext) -> str:
    context.log.architecture = {
        "name": arguments.get("name"),
        "summary": arguments.get("summary"),
        "layers": arguments.get("layers"),
        "steps": arguments.get("steps"),
    }
    return "Architecture enregistrée.\n" + json.dumps(context.log.architecture, ensure_ascii=False, indent=2)
