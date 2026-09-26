import shutil
import subprocess
from pathlib import Path

EXTENSION = "bierner.markdown-mermaid"
APP_CLI = Path("/Applications/Cursor.app/Contents/Resources/app/bin/cursor")


def install_mermaid_extension() -> str:
    binary = _cursor_cli()
    if binary is None:
        return "CLI Cursor introuvable. Installe l'extension Markdown Preview Mermaid Support à la main."
    try:
        completed = subprocess.run(
            [str(binary), "--install-extension", EXTENSION],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"Installation Mermaid échouée : {exc}"
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        return f"Installation Mermaid échouée : {detail}"
    return "Extension Mermaid prête. Ouvre modelisation.md puis l'aperçu Markdown."


def _cursor_cli() -> Path | None:
    if APP_CLI.is_file():
        return APP_CLI
    found = shutil.which("cursor") or shutil.which("code")
    return Path(found) if found else None
