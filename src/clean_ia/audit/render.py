from clean_ia.models import AuditFinding, AuditReport

_TITLES = {
    "clean-code": "Audit clean code",
    "securite": "Audit sécurité",
}


def render_audit(report: AuditReport) -> str:
    counts = _counts(report.findings)
    lines = [
        f"# {_TITLES.get(report.kind, 'Audit')}",
        "",
        f"Projet : {report.root}",
        f"Fichiers : {report.file_count}",
        (
            f"Constats : {len(report.findings)} "
            f"(haute : {counts['haute']}, moyenne : {counts['moyenne']}, basse : {counts['basse']})"
        ),
        "",
        "## Synthèse",
        "",
        _summary(report, counts),
        "",
        "## Constats",
        "",
    ]
    if not report.findings:
        lines.append("Aucun constat.")
    else:
        for index, finding in enumerate(report.findings, start=1):
            lines.extend(_finding(index, finding))
    lines.extend(
        [
            "",
            "## Périmètre",
            "",
            "Analyse statique du code source. Elle ne lance pas le projet et ne remplace pas une revue humaine.",
            "",
        ]
    )
    return "\n".join(lines)


def _summary(report: AuditReport, counts: dict[str, int]) -> str:
    if not report.findings:
        if report.kind == "securite":
            return "Aucun problème de sécurité détecté par les règles locales."
        return "Aucun problème de clean code détecté par les règles locales."
    return (
        f"{len(report.findings)} constat(s) : "
        f"{counts['haute']} de sévérité haute, {counts['moyenne']} moyenne, {counts['basse']} basse."
    )


def _finding(index: int, finding: AuditFinding) -> list[str]:
    return [
        f"### {index}. [{finding.severity}] {finding.code} — `{finding.path}:{finding.line}`",
        "",
        finding.message,
        "",
        f"**Recommandation.** {finding.recommendation}",
        "",
    ]


def _counts(findings: list[AuditFinding]) -> dict[str, int]:
    counts = {"haute": 0, "moyenne": 0, "basse": 0}
    for finding in findings:
        if finding.severity in counts:
            counts[finding.severity] += 1
    return counts
