import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "composer-2.5"


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    model: str
    max_tokens: int
    max_turns: int


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def load_settings(max_turns: int = 24, model: str | None = None) -> Settings:
    _load_dotenv(Path.cwd() / ".env")
    return Settings(
        api_key=os.environ.get("CURSOR_API_KEY") or None,
        model=model or os.environ.get("CLEAN_IA_MODEL") or DEFAULT_MODEL,
        max_tokens=16000,
        max_turns=max_turns,
    )


def require_api_key(settings: Settings) -> str:
    if not settings.api_key:
        raise ConfigError(
            "CURSOR_API_KEY est absent. Ajoute-le dans l'environnement ou dans un fichier .env."
        )
    return settings.api_key
