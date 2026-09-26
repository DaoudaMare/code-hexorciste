import ast
import re
from pathlib import Path

from clean_ia.analyzer.scanner import language_of, read_text
from clean_ia.models import ImportRef, ParsedFile, Symbol

_JS_FUNCTION = re.compile(
    r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)",
    re.MULTILINE,
)
_JS_CLASS = re.compile(r"^(?:export\s+)?class\s+(\w+)", re.MULTILINE)
_JS_IMPORT = re.compile(
    r"""^import\s+(?:.+?\s+from\s+)?['"]([^'"]+)['"]""",
    re.MULTILINE,
)
_JS_REQUIRE = re.compile(r"""require\(\s*['"]([^'"]+)['"]\s*\)""")


def parse_file(path: Path) -> ParsedFile | None:
    text = read_text(path)
    if text is None:
        return None
    language = language_of(path)
    lines = text.count("\n") + (0 if text.endswith("\n") or text == "" else 1)
    parsed = ParsedFile(path=path, language=language, text=text, lines=lines)
    if language == "python":
        _parse_python(parsed)
    elif language in {"javascript", "typescript"}:
        _parse_javascript(parsed)
    return parsed


def _parse_python(parsed: ParsedFile) -> None:
    try:
        tree = ast.parse(parsed.text)
    except SyntaxError as exc:
        parsed.parse_error = str(exc)
        return
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            parsed.symbols.append(_function_symbol(node, parent=None))
        elif isinstance(node, ast.ClassDef):
            parsed.symbols.append(
                Symbol(
                    name=node.name,
                    kind="class",
                    lineno=node.lineno,
                    end_lineno=node.end_lineno or node.lineno,
                )
            )
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    parsed.symbols.append(_function_symbol(child, parent=node.name))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                parsed.imports.append(
                    ImportRef(module=alias.name, names=(), lineno=node.lineno, kind="import")
                )
        elif isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            names = tuple(alias.name for alias in node.names)
            parsed.imports.append(
                ImportRef(module=module, names=names, lineno=node.lineno, kind="from")
            )


def _function_symbol(node: ast.AST, parent: str | None) -> Symbol:
    kind = "method" if parent else "function"
    return Symbol(
        name=node.name,
        kind=kind,
        lineno=node.lineno,
        end_lineno=getattr(node, "end_lineno", None) or node.lineno,
        parent=parent,
    )


def _parse_javascript(parsed: ParsedFile) -> None:
    for match in _JS_FUNCTION.finditer(parsed.text):
        lineno = parsed.text[: match.start()].count("\n") + 1
        parsed.symbols.append(
            Symbol(name=match.group(1), kind="function", lineno=lineno, end_lineno=lineno)
        )
    for match in _JS_CLASS.finditer(parsed.text):
        lineno = parsed.text[: match.start()].count("\n") + 1
        parsed.symbols.append(
            Symbol(name=match.group(1), kind="class", lineno=lineno, end_lineno=lineno)
        )
    for match in _JS_IMPORT.finditer(parsed.text):
        lineno = parsed.text[: match.start()].count("\n") + 1
        parsed.imports.append(
            ImportRef(module=match.group(1), names=(), lineno=lineno, kind="import")
        )
    for match in _JS_REQUIRE.finditer(parsed.text):
        lineno = parsed.text[: match.start()].count("\n") + 1
        parsed.imports.append(
            ImportRef(module=match.group(1), names=(), lineno=lineno, kind="require")
        )
