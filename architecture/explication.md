# Explication — architecture en couches pour clean-ia

## Pourquoi

Le projet mélange aujourd'hui analyse statique, orchestration LLM, persistance et CLI dans une arborescence « par fonctionnalité » (`analyzer/`, `orchestrator/`, `cli/`). Cela reste lisible à ~30 fichiers, mais les frontières ne sont pas explicites : `orchestrator/agent.py` importe directement l'infrastructure (index, Cursor, config) et le formatage de rapport (`analyzer/service.py`).

L'objectif du refactor (sans changer le comportement) est de :

1. **Isoler** les modèles et règles (`models`, smells, plan d'architecture heuristique).
2. **Extraire** les fonctions trop longues — notamment `main` dans `cli/main.py` (~50 lignes, smell `function-too-long`).
3. **Pousser** disque, réseau (`cursor-sdk`), subprocess et `.env` vers **infrastructure**.
4. **Garder** la CLI et `__main__.py` comme **adaptateurs minces** qui appellent des cas d'usage.

État actuel relevé par l'analyseur : **31 fichiers**, **0 cycle d'import**, **1 smell** (`function-too-long` sur `main`).

## Avantages

- **Tests unitaires plus simples** : `domain` et une partie de `application` se testent sans Cursor ni disque (comme aujourd'hui pour smells/cycles via `ProjectAnalyzer`, mais avec moins de couplage).
- **Évolution de l'agent** : remplacer `CursorClient` ou les outils fichiers ne touche pas aux règles smells ni au modèle `ProjectReport`.
- **CLI stable** : `pyproject.toml` peut continuer à exposer `clean-ia` ; seul le module importé change (`interfaces.cli.main:main`).
- **Alignement avec le produit** : l'outil propose déjà une « architecture en couches » aux projets analysés ; appliquer la même structure à `clean_ia` sert d'exemple cohérent.

## Inconvénients

- **Plus de dossiers** pour un petit package : navigation légèrement plus longue avant d'être habitué à la carte.
- **Migration mécanique** : déplacer ~25 modules implique mettre à jour tous les imports et `tests/test_clean_ia.py` (risque de régression si un re-export public est oublié).
- **Pas de ports explicites (interfaces Python)** : l'application appellera encore des classes concrètes d'infrastructure ; ce n'est pas de l'hexagonal strict, seulement des couches pragmatiques. Introduire des Protocol pour `LlmClient` ou `ExampleStore` serait un surcoût pour l'instant.
- **`tools/registry`** n'est pas branché sur `Orchestrator` aujourd'hui (utilisé surtout en tests) : lors du déplacement, éviter de créer une fausse dépendance application → tools tant que l'agent Cursor ne les invoque pas localement.

## Ordre de migration recommandé

1. Créer les dossiers `domain/`, `application/`, `infrastructure/`, `interfaces/` avec des `__init__.py` et des re-exports temporaires depuis les anciens chemins (compatibilité une release).
2. Déplacer `models.py` → `domain/models/` puis ajuster les imports.
3. Scinder `analyzer/service.py` : logique `ProjectAnalyzer` → `application/analyze.py`, `render_report` → `application/report.py` ; scanner/parser/deps → `infrastructure/analysis/`.
4. Déplacer `Orchestrator` → `application/agent_session.py` ; heuristic/prompts → `domain/`.
5. Refactor CLI : `build_parser()` + `dispatch(args)` dans `interfaces/cli/` (corrige le smell sans changer les sous-commandes).
6. Supprimer les anciens packages vides (`analyzer/`, `orchestrator/` au niveau racine) et les re-exports une fois les tests verts.
7. Lancer `python3 -m pytest -q` (comme dans `tests/test_clean_ia.py`).

## Risques à surveiller

| Risque | Mitigation |
| --- | --- |
| Casser le point d'entrée `clean-ia` | Mettre à jour `[project.scripts]` vers `clean_ia.interfaces.cli.main:main` et garder un alias deprecated une version. |
| Secrets | Ne pas déplacer la logique `PROTECTED` / `.env` hors de `infrastructure` ; ne jamais committer `.env`. |
| Comportement agent | Ne pas modifier `prompts.py` ni les chaînes de mode plan/apply dans le même PR que les moves. |
| Régression analyze | `ProjectAnalyzer` doit produire le même `ProjectReport` (tests existants smells/cycles/langues). |

## Détail agent (session actuelle)

Cette proposition documente la cible et les diffs de refactor **sans modifier le code applicatif** (hors création de `architecture/modelisation.md` et `architecture/explication.md`). Les diffs concrets pour `cli/main.py` et la carte des déplacements sont décrits dans la réponse de l'agent clean-code.
