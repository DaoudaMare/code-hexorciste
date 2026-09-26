import re

from clean_ia.models import AuditFinding, ProjectReport

_SEVERITY = {"haute": 0, "moyenne": 1, "basse": 2}

_CLEAN = {
    "parse-error": ("haute", "Corriger la syntaxe avant de poursuivre l'audit."),
    "file-too-long": ("moyenne", "Découper le fichier par responsabilité."),
    "function-too-long": ("moyenne", "Extraire des fonctions plus courtes, une intention chacune."),
    "large-class": ("moyenne", "Séparer les responsabilités de la classe."),
    "too-many-params": ("basse", "Réduire la signature ou regrouper les paramètres."),
    "bare-except": ("basse", "Attraper une exception précise."),
}

_SKIP_NAMES = {"main", "setUp", "tearDown"}

_SECRET = re.compile(
    r"""(?ix)
    \b(?P<name>password|passwd|pwd|api[_-]?key|apikey|secret|access[_-]?key|private[_-]?key|token)
    ['\"]?
    \s*[:=]\s*
    (?P<quote>['\"])
    (?P<value>[^'\"]+)
    (?P=quote)
    """
)

_PLACEHOLDERS = {
    "changeme",
    "change-me",
    "change_me",
    "password",
    "secret",
    "token",
    "todo",
    "xxx",
    "xxxx",
    "xxxxxxxx",
    "example",
    "dummy",
    "placeholder",
    "your-api-key",
    "your_api_key",
    "redacted",
}

_CHECKS = (
    (
        "shell-true",
        "haute",
        "Commande lancée via le shell.",
        "Passer les arguments en liste, sans shell.",
        re.compile(r"\bshell\s*=\s*True\b"),
    ),
    (
        "dynamic-exec",
        "haute",
        "Exécution de code construit dynamiquement.",
        "Remplacer eval ou exec par un appel explicite.",
        re.compile(r"\b(eval|exec)\s*\("),
    ),
    (
        "unsafe-deserialize",
        "haute",
        "Désérialisation non sûre.",
        "Éviter pickle sur des données non fiables, et charger le YAML avec un loader sûr.",
        re.compile(r"\bpickle\.loads?\s*\(|\byaml\.load\s*\("),
    ),
    (
        "tls-verify-disabled",
        "moyenne",
        "Vérification TLS désactivée.",
        "Laisser la vérification des certificats active.",
        re.compile(r"\bverify\s*=\s*False\b"),
    ),
    (
        "sql-interpolation",
        "haute",
        "Requête SQL construite par interpolation.",
        "Utiliser une requête paramétrée.",
        re.compile(r"""\.execute\(\s*f['\"]"""),
    ),
    (
        "dom-html-sink",
        "moyenne",
        "HTML injecté dans le DOM.",
        "Insérer du texte, ou échapper le HTML avant de l'afficher.",
        re.compile(r"\binnerHTML\b|dangerouslySetInnerHTML"),
    ),
)


def clean_code_findings(report: ProjectReport) -> list[AuditFinding]:
    findings = [_from_smell(smell) for smell in report.smells if _in_scope(smell.path)]
    findings.extend(_cycles(report))
    findings.extend(_unused(report))
    return _sorted(findings)


def security_findings(report: ProjectReport) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for item in report.files:
        if item.language == "markdown":
            continue
        rel = item.relative(report.root)
        if not _in_scope(rel):
            continue
        for lineno, line in enumerate(item.text.splitlines(), start=1):
            findings.extend(_security_line(rel, lineno, line))
    return _sorted(findings)


def _from_smell(smell) -> AuditFinding:
    severity, recommendation = _CLEAN.get(smell.code, ("moyenne", "Revoir ce point avant de l'étendre."))
    return AuditFinding(smell.path, smell.line, smell.code, severity, smell.message, recommendation)


def _cycles(report: ProjectReport) -> list[AuditFinding]:
    found: list[AuditFinding] = []
    for cycle in report.cycles:
        path = cycle[0] if cycle else ""
        if not _in_scope(path):
            continue
        found.append(
            AuditFinding(
                path,
                1,
                "import-cycle",
                "haute",
                "Import circulaire : " + " -> ".join(cycle),
                "Extraire la dépendance partagée pour casser le cycle.",
            )
        )
    return found


def _unused(report: ProjectReport) -> list[AuditFinding]:
    corpus = "\n".join(item.text for item in report.files if _in_scope(item.relative(report.root)))
    found: list[AuditFinding] = []
    for item in report.files:
        if item.language != "python":
            continue
        rel = item.relative(report.root)
        if not _in_scope(rel):
            continue
        for symbol in item.symbols:
            if symbol.kind not in {"function", "method"}:
                continue
            if symbol.name.startswith("_") or symbol.name in _SKIP_NAMES or symbol.name.startswith("test"):
                continue
            if corpus.count(symbol.name) > 1:
                continue
            found.append(
                AuditFinding(
                    rel,
                    symbol.lineno,
                    "dead-code",
                    "basse",
                    f"{symbol.qualified} n'a pas d'autre référence dans le projet.",
                    "Retirer la fonction une fois vérifié qu'aucun appel ne reste.",
                )
            )
    return found


def _security_line(path: str, lineno: int, line: str) -> list[AuditFinding]:
    found: list[AuditFinding] = []
    secret = _secret_name(line)
    if secret:
        found.append(
            AuditFinding(
                path,
                lineno,
                "hardcoded-secret",
                "haute",
                f"Secret en dur ({secret}).",
                "Lire le secret depuis l'environnement ou un coffre, et le retirer du dépôt.",
            )
        )
    if "PRIVATE KEY" in line and "BEGIN" in line:
        found.append(
            AuditFinding(
                path,
                lineno,
                "private-key",
                "haute",
                "Clé privée présente dans le source.",
                "Retirer la clé du dépôt et la faire tourner.",
            )
        )
    for code, severity, message, recommendation, pattern in _CHECKS:
        if not pattern.search(line):
            continue
        if code == "unsafe-deserialize" and "SafeLoader" in line:
            continue
        found.append(AuditFinding(path, lineno, code, severity, message, recommendation))
    return found


def _secret_name(line: str) -> str | None:
    match = _SECRET.search(line)
    if match is None:
        return None
    value = match.group("value").strip()
    if len(value) < 8 or _placeholder(value):
        return None
    return match.group("name").lower().replace("-", "_")


def _placeholder(value: str) -> bool:
    folded = value.strip().lower()
    if folded in _PLACEHOLDERS or set(folded) <= {"*", "x", "."}:
        return True
    markers = ("example", "placeholder", "changeme", "your_", "your-", "todo", "dummy", "redacted")
    return any(marker in folded for marker in markers)


def _in_scope(path: str) -> bool:
    return path != "audits" and not path.startswith("audits/")


def _sorted(findings: list[AuditFinding]) -> list[AuditFinding]:
    return sorted(findings, key=lambda item: (_SEVERITY.get(item.severity, 9), item.path, item.line, item.code))
