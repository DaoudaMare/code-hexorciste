# Modélisation — clean-ia (architecture en couches)

Vue cible pour le package `clean_ia` sous `src/clean_ia/`. Les flèches indiquent la direction des dépendances autorisées (du haut vers le bas).

```mermaid
flowchart TB
  subgraph interfaces["interfaces — points d'entrée"]
    CLI["cli/ (argparse, commandes)"]
    MAIN["__main__.py"]
  end

  subgraph application["application — cas d'usage"]
    UC_ANALYZE["AnalyzeProject"]
    UC_REPORT["FormatProjectReport"]
    UC_AGENT["AgentSession (suggest / refactor / chat)"]
    UC_TRAIN["ManageTrainingExamples"]
  end

  subgraph domain["domain — métier pur"]
    MODELS["entities & value objects"]
    SMELLS["règles de smells"]
    ARCH_PLAN["heuristique d'architecture"]
    PROMPTS["contrats de prompts (texte)"]
  end

  subgraph infrastructure["infrastructure — I/O & frameworks"]
    FS_SCAN["scanner / parser / dépendances"]
    CONFIG["config & .env"]
    INDEX["chunker / TF-IDF / CodeIndex"]
    LLM["CursorClient (cursor-sdk)"]
    PERSIST["memory session, docs architecture, JSONL training"]
    TOOLS["registry outils (fichiers, git, tests)"]
  end

  MAIN --> CLI
  CLI --> UC_ANALYZE
  CLI --> UC_AGENT
  CLI --> UC_TRAIN

  UC_ANALYZE --> MODELS
  UC_ANALYZE --> SMELLS
  UC_ANALYZE --> FS_SCAN
  UC_REPORT --> MODELS

  UC_AGENT --> ARCH_PLAN
  UC_AGENT --> PROMPTS
  UC_AGENT --> UC_ANALYZE
  UC_AGENT --> INDEX
  UC_AGENT --> LLM
  UC_AGENT --> PERSIST
  UC_AGENT --> CONFIG

  UC_TRAIN --> MODELS
  UC_TRAIN --> PERSIST
  UC_TRAIN --> INDEX

  SMELLS --> MODELS
  ARCH_PLAN --> MODELS
  FS_SCAN --> MODELS
  INDEX --> MODELS
  PERSIST --> MODELS
  TOOLS --> MODELS
  TOOLS --> INDEX
```

## Correspondance actuelle → cible

| Emplacement actuel | Couche cible | Rôle |
| --- | --- | --- |
| `models.py` | `domain/models/` | Entités : `ProjectReport`, `ParsedFile`, `Smell`, `AgentResult`, etc. |
| `analyzer/smells.py` | `domain/analysis/smells.py` | Seuils et détection de smells (sans I/O). |
| `orchestrator/heuristic.py` | `domain/architecture/planning.py` | Plan en couches à partir d'un `ProjectReport`. |
| `orchestrator/prompts.py` | `domain/agent/prompts.py` | Textes système / utilisateur (pas d'appel réseau). |
| `analyzer/service.py` (`ProjectAnalyzer`, `render_report`) | `application/analyze.py` + `application/report.py` | Cas d'usage « analyser » et formatage texte du rapport. |
| `orchestrator/agent.py` | `application/agent_session.py` | Orchestration suggest / refactor / chat. |
| `training/dataset.py` (logique métier) | `application/training.py` | Charger / ajouter / sélectionner des exemples. |
| `analyzer/scanner.py`, `parser.py`, `dependencies.py` | `infrastructure/analysis/` | Lecture disque, AST, graphe d'imports. |
| `config.py` | `infrastructure/config/` | Variables d'environnement et `Settings`. |
| `index/*` | `infrastructure/index/` | Découpage et recherche TF-IDF. |
| `llm/cursor.py` | `infrastructure/llm/cursor.py` | Adaptateur `cursor-sdk`. |
| `orchestrator/memory.py`, `architecture_docs.py` | `infrastructure/persistence/` | Session JSON, écriture `architecture/*.md`. |
| `tools/registry.py` | `infrastructure/tools/` | Fichiers, subprocess tests, git. |
| `cli/main.py`, `__main__.py` | `interfaces/cli/` | Parsing CLI mince + dispatch vers l'application. |

## Modules internes (détail)

```mermaid
flowchart LR
  subgraph domain_detail["domain"]
    M[models]
    S[smells]
    H[architecture planning]
    P[prompts]
  end

  subgraph app_detail["application"]
    PA[ProjectAnalyzer use case]
    RF[render_report]
    OR[Orchestrator]
    TR[training service]
  end

  subgraph infra_detail["infrastructure"]
    SC[scanner]
    PR[parser]
    DP[dependencies]
    CF[config]
    CI[CodeIndex]
    CU[CursorClient]
    MEM[Memory]
    AD[architecture_docs]
    RG[tools registry]
  end

  PA --> M
  PA --> S
  PA --> SC
  PA --> PR
  PA --> DP
  RF --> M
  OR --> H
  OR --> P
  OR --> PA
  OR --> RF
  OR --> CI
  OR --> CU
  OR --> MEM
  OR --> AD
  OR --> CF
  TR --> M
  TR --> AD
  S --> M
  H --> M
  SC --> M
  PR --> M
  DP --> M
  CI --> M
  RG --> M
  RG --> CI
```

## Couches (rappel)

- **domain** : `src/clean_ia/domain/` — modèles, règles smells, heuristique d'architecture, prompts.
- **application** : `src/clean_ia/application/` — analyser un projet, formater un rapport, session agent, gestion des exemples d'entraînement.
- **infrastructure** : `src/clean_ia/infrastructure/` — disque, AST, index, API Cursor, cache, outils fichiers/git/tests.
- **interfaces** : `src/clean_ia/interfaces/cli/` — `clean-ia` (entry point `pyproject.toml` inchangé en nom, chemin Python mis à jour).
