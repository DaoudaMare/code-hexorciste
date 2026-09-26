import json
from pathlib import Path


class Memory:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    def add_user(self, content) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, content: list[dict]) -> None:
        self.messages.append({"role": "assistant", "content": content})

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.messages, ensure_ascii=False), encoding="utf-8")

    def load(self, path: Path) -> None:
        if path.is_file():
            self.messages = json.loads(path.read_text(encoding="utf-8"))
