from pathlib import Path

from clean_ia.analyzer.service import ProjectAnalyzer
from clean_ia.audit.render import render_audit
from clean_ia.audit.rules import clean_code_findings, security_findings
from clean_ia.models import AuditReport

_FILES = {
    "clean-code": "clean-code.md",
    "securite": "securite.md",
}

_KINDS = {
    "clean-code": "clean-code",
    "cleancode": "clean-code",
    "clean": "clean-code",
    "securite": "securite",
    "security": "securite",
    "sécurité": "securite",
}


def run_audit(root: Path, kind: str) -> AuditReport:
    normalized = normalize_kind(kind)
    project = ProjectAnalyzer(root).analyze()
    findings = clean_code_findings(project) if normalized == "clean-code" else security_findings(project)
    return AuditReport(kind=normalized, root=project.root, file_count=len(project.files), findings=findings)


def write_audit(report: AuditReport, destination: Path | None = None) -> Path:
    path = destination or (report.root / "audits" / _FILES[report.kind])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_audit(report), encoding="utf-8")
    return path


def normalize_kind(kind: str) -> str:
    normalized = _KINDS.get(kind.strip().lower())
    if normalized is None:
        raise ValueError("Audit inconnu. Choisir clean-code ou securite.")
    return normalized
