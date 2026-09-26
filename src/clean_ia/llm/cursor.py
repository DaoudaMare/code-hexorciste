from pathlib import Path

from clean_ia.config import ConfigError


class CursorClient:
    """Agent Cursor local : le modèle lit et modifie le projet lui-même."""

    def __init__(self, api_key: str, model: str, cwd: Path):
        try:
            from cursor_sdk import Agent, CursorAgentError, LocalAgentOptions
        except ImportError as exc:
            raise ConfigError("Installe la dépendance : pip install -e .") from exc
        self._error = CursorAgentError
        self._context = Agent.create(
            model=model,
            api_key=api_key,
            local=LocalAgentOptions(cwd=str(cwd)),
        )
        self._agent = None

    def send(self, prompt: str) -> str:
        agent = self._ensure()
        try:
            run = agent.send(prompt)
            chunks = _stream(run)
            result = run.wait()
        except self._error as exc:
            raise ConfigError(f"Cursor : {exc.message}") from exc
        if getattr(result, "status", None) == "error":
            raise ConfigError(f"Run Cursor en erreur : {getattr(result, 'id', '')}")
        return "".join(chunks).strip() or (getattr(result, "result", None) or "").strip()

    def close(self) -> None:
        if self._agent is None:
            return
        self._context.__exit__(None, None, None)
        self._agent = None

    def _ensure(self):
        if self._agent is None:
            self._agent = self._context.__enter__()
        return self._agent


def _stream(run) -> list[str]:
    chunks: list[str] = []
    for message in run.messages():
        if getattr(message, "type", None) != "assistant":
            continue
        content = getattr(getattr(message, "message", None), "content", []) or []
        for block in content:
            if getattr(block, "type", None) == "text" and getattr(block, "text", None):
                print(block.text, end="", flush=True)
                chunks.append(block.text)
    if chunks:
        print(flush=True)
    return chunks
