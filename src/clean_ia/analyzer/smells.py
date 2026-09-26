import ast

from clean_ia.models import ParsedFile, Smell

FILE_LINE_LIMIT = 400
FUNCTION_LINE_LIMIT = 40
METHOD_COUNT_LIMIT = 15
PARAM_LIMIT = 5


def detect_smells(root_name, files: list[ParsedFile]) -> list[Smell]:
    smells: list[Smell] = []
    for item in files:
        rel = item.relative(root_name)
        if item.lines > FILE_LINE_LIMIT:
            smells.append(
                Smell(rel, 1, "file-too-long", f"Fichier long ({item.lines} lignes).")
            )
        if item.parse_error:
            smells.append(Smell(rel, 1, "parse-error", f"Syntaxe invalide : {item.parse_error}"))
        if item.language == "python":
            smells.extend(_python_smells(rel, item))
    return smells


def _python_smells(rel: str, item: ParsedFile) -> list[Smell]:
    found = _symbol_smells(rel, item)
    try:
        tree = ast.parse(item.text)
    except SyntaxError:
        return found
    found.extend(_ast_smells(rel, tree))
    return found


def _symbol_smells(rel: str, item: ParsedFile) -> list[Smell]:
    found: list[Smell] = []
    methods_by_class: dict[str, int] = {}
    for symbol in item.symbols:
        length = symbol.end_lineno - symbol.lineno + 1
        if symbol.kind in {"function", "method"} and length > FUNCTION_LINE_LIMIT:
            found.append(
                Smell(rel, symbol.lineno, "function-too-long", f"{symbol.qualified} fait {length} lignes.")
            )
        if symbol.kind == "method" and symbol.parent:
            methods_by_class[symbol.parent] = methods_by_class.get(symbol.parent, 0) + 1
    for class_name, count in methods_by_class.items():
        if count > METHOD_COUNT_LIMIT:
            found.append(Smell(rel, 1, "large-class", f"{class_name} a {count} méthodes."))
    return found


def _ast_smells(rel: str, tree: ast.AST) -> list[Smell]:
    found: list[Smell] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            total = len(node.args.args) + len(node.args.posonlyargs) + len(node.args.kwonlyargs)
            if total > PARAM_LIMIT:
                found.append(Smell(rel, node.lineno, "too-many-params", f"{node.name} a {total} paramètres."))
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            found.append(Smell(rel, node.lineno, "bare-except", "except nu."))
    return found
