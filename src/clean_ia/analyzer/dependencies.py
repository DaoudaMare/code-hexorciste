import json
import tomllib
from pathlib import Path

from clean_ia.models import ExternalDependency, ParsedFile


def collect_external(root: Path) -> list[ExternalDependency]:
    found: list[ExternalDependency] = []
    requirements = root / "requirements.txt"
    if requirements.is_file():
        for line in requirements.read_text(encoding="utf-8", errors="replace").splitlines():
            name = line.strip()
            if not name or name.startswith("#") or name.startswith("-"):
                continue
            found.append(ExternalDependency(name=_package_name(name), source="requirements.txt"))
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        found.extend(_pyproject_deps(pyproject))
    package_json = root / "package.json"
    if package_json.is_file():
        found.extend(_npm_deps(package_json))
    return found


def local_import_graph(root: Path, files: list[ParsedFile]) -> dict[str, set[str]]:
    modules = {_module_name(root, item.path): item.relative(root) for item in files if item.language == "python"}
    graph: dict[str, set[str]] = {rel: set() for rel in modules.values()}
    by_module = {module: rel for module, rel in modules.items()}
    for item in files:
        if item.language != "python":
            continue
        source = item.relative(root)
        for ref in item.imports:
            target = _resolve_local(ref.module, source, by_module)
            if target and target != source:
                graph[source].add(target)
    return graph


def find_cycles(graph: dict[str, set[str]]) -> list[tuple[str, ...]]:
    cycles: list[tuple[str, ...]] = []
    seen: set[str] = set()

    def visit(node: str, stack: list[str]) -> None:
        if node in stack:
            start = stack.index(node)
            cycle = tuple(stack[start:] + [node])
            if cycle not in cycles:
                cycles.append(cycle)
            return
        if node in seen:
            return
        seen.add(node)
        stack.append(node)
        for nxt in sorted(graph.get(node, ())):
            visit(nxt, stack)
        stack.pop()

    for node in sorted(graph):
        visit(node, [])
    return cycles


def _package_name(spec: str) -> str:
    for sep in ("==", ">=", "<=", "~=", "!=", ">", "<", "["):
        spec = spec.split(sep, 1)[0]
    return spec.strip()


def _pyproject_deps(path: Path) -> list[ExternalDependency]:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return []
    project = data.get("project", {})
    deps = list(project.get("dependencies", []))
    groups = project.get("optional-dependencies", {})
    for names in groups.values():
        deps.extend(names)
    return [ExternalDependency(name=_package_name(str(dep)), source="pyproject.toml") for dep in deps]


def _npm_deps(path: Path) -> list[ExternalDependency]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    names: list[str] = []
    for key in ("dependencies", "devDependencies"):
        names.extend(data.get(key, {}))
    return [ExternalDependency(name=name, source="package.json") for name in names]


def _module_name(root: Path, path: Path) -> str:
    rel = path.relative_to(root).as_posix()
    if rel.endswith(".py"):
        rel = rel[:-3]
    parts = [part for part in rel.split("/") if part and part != "__init__"]
    if parts and parts[0] == "src":
        parts = parts[1:]
    return ".".join(parts)


def _resolve_local(module: str, source: str, by_module: dict[str, str]) -> str | None:
    cleaned = module.lstrip(".")
    if not cleaned:
        return None
    if cleaned in by_module:
        return by_module[cleaned]
    parent = source.rsplit("/", 1)[0] if "/" in source else ""
    candidate = f"{parent.replace('/', '.')}.{cleaned}" if parent else cleaned
    return by_module.get(candidate)
