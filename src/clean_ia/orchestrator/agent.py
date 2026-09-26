from clean_ia.analyzer.service import render_report
from clean_ia.config import Settings, require_api_key
from clean_ia.index.store import CodeIndex
from clean_ia.llm.cursor import CursorClient
from clean_ia.models import AgentResult, ProjectReport, RunLog
from clean_ia.orchestrator.architecture_docs import ensure_architecture_docs
from clean_ia.orchestrator.mermaid_ext import install_mermaid_extension
from clean_ia.orchestrator.heuristic import cache_dir, format_architecture, suggest_architecture
from clean_ia.orchestrator.inventory import render_inventory
from clean_ia.orchestrator.memory import Memory
from clean_ia.orchestrator.prompts import SYSTEM, user_prompt
from clean_ia.training.dataset import format_examples, load_examples, relevant_examples


class Orchestrator:
    """Boucle de l'agent : contexte et appels à l'agent Cursor local."""

    def __init__(self, report: ProjectReport, settings: Settings, apply: bool, writes_enabled: bool):
        self.report = report
        self.settings = settings
        self.apply = apply
        self.writes_enabled = writes_enabled
        self.memory = Memory()
        self.log = RunLog()
        self.index = CodeIndex()
        self.index.build(report)
        self._client: CursorClient | None = None
        self._primed = False

    def suggest(self) -> AgentResult:
        local = suggest_architecture(self.report)
        self.log.architecture = local
        if not self.settings.api_key:
            ensure_architecture_docs(self.report.root, local)
            self.log.notes.append(install_mermaid_extension())
            return AgentResult(format_architecture(local), self.log)
        try:
            text = self._run(
                "Propose une architecture et écris architecture/modelisation.md "
                "et architecture/explication.md. Le schéma est en Mermaid. "
                "Ne modifie aucun autre fichier.\n\n"
                + user_prompt(render_report(self.report), format_architecture(local), None, False)
            )
            ensure_architecture_docs(self.report.root, local, text)
            self.log.notes.append(install_mermaid_extension())
            return AgentResult(text, self.log)
        finally:
            self.close()

    def refactor(self, target: str | None) -> AgentResult:
        local = format_architecture(suggest_architecture(self.report))
        try:
            text = self._run(user_prompt(render_report(self.report), local, target, self.apply and self.writes_enabled))
            return AgentResult(text, self.log)
        finally:
            self.close()

    def chat(self, message: str, resume: bool = False) -> str:
        path = cache_dir(self.report.root) / "session.json"
        if resume:
            self.memory.load(path)
        if not self.memory.messages:
            brief = render_report(self.report, limit=40)
            self.memory.add_user(f"Contexte du projet :\n{brief}")
            self.memory.add_assistant(
                [{"type": "text", "text": "Contexte chargé. Décris l'architecture voulue ou demande une suggestion."}]
            )
        try:
            text = self._run(message)
        except Exception:
            if self.memory.messages and self.memory.messages[-1]["role"] == "user":
                self.memory.messages.pop()
            raise
        self.memory.save(path)
        return text

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _run(self, message: str) -> str:
        client = self._llm()
        mode = (
            "Tu peux modifier les fichiers du projet. "
            "Si tu proposes une architecture, écris aussi architecture/modelisation.md et architecture/explication.md."
            if self.apply and self.writes_enabled
            else "Ne modifie pas le code. Tu peux seulement créer ou mettre à jour "
            "architecture/modelisation.md et architecture/explication.md."
        )
        context = ""
        if not self._primed:
            context = (
                f"Analyse du projet :\n{render_report(self.report, limit=40)}\n\n"
                f"{render_inventory(self.report)}\n\n"
            )
            self._primed = True
        prompt = f"{SYSTEM}\n\n{mode}\n\n{context}{self._with_training(message)}"
        self.memory.add_user(prompt)
        text = client.send(prompt)
        self.memory.add_assistant([{"type": "text", "text": text}])
        return text or "Terminé."

    def _with_training(self, message: str) -> str:
        chosen = relevant_examples(message, load_examples(), limit=4)
        block = format_examples(chosen)
        if not block:
            return message
        print(f"Exemples d'entraînement utilisés : {len(chosen)}", flush=True)
        return f"{block}\n\n{message}"

    def _llm(self) -> CursorClient:
        if self._client is None:
            self._client = CursorClient(
                api_key=require_api_key(self.settings),
                model=self.settings.model,
                cwd=self.report.root,
            )
        return self._client
