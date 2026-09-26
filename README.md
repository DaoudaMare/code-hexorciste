# clean-ia

Agent Python qui analyse un projet existant et le refactorise vers une architecture que tu imposes, ou vers celle qu'il propose.

Il ne rajoute pas de fonctionnalité. Il range le code déjà là : architecture hexagonale, Repository, SOLID, TDD, clean code, et suppression du code mort une fois vérifié qu'aucun appel ne reste. Il peut aussi créer un projet Python ou Flutter qui ne contient que cette structure.

```
CLI
 └─ Orchestrateur
     ├─ Analyseur (scan, AST, dépendances, cycles)
     ├─ Index (découpage + recherche)
     ├─ Cursor (agent local)
     └─ Outils : read_file, write_file, list_directory, run_tests, git_diff
```

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

`CURSOR_API_KEY` est nécessaire pour `suggest`, `refactor` et `chat`. Le modèle par défaut est `composer-2.5`. `analyze`, `audit` et `new` fonctionnent sans clé.

## Usage

```bash
clean-ia analyze ./mon-projet
clean-ia audit clean-code ./mon-projet
clean-ia audit securite ./mon-projet
clean-ia suggest ./mon-projet
clean-ia refactor ./mon-projet --arch hexagonal
clean-ia refactor ./mon-projet --arch tdd --apply
clean-ia refactor ./mon-projet --arch hexa-tdd --apply
clean-ia refactor ./mon-projet --arch-file archi.txt
clean-ia chat ./mon-projet
clean-ia new python ./mon-projet --arch hexagonal,tdd
clean-ia new flutter ./mon-app --arch hexagonal
clean-ia train add --instruction "Découpe ce fichier en couches." --output "Domain sans framework, application pour les cas d'usage, infrastructure pour le disque."
clean-ia train list
```

`analyze` scanne le projet, parse le code, relève les dépendances et les problèmes de structure (fichier trop long, fonction trop longue, classe trop grosse, trop de paramètres, `except` nu). Les cycles d'import sont calculés pour Python.

`audit` écrit `audits/clean-code.md` ou `audits/securite.md` dans le projet. L'audit sécurité cherche notamment les secrets en dur, `shell=True`, `eval`/`exec`, pickle, TLS désactivé et le SQL interpolé.

`suggest` propose une architecture hexagonale et écrit `architecture/modelisation.md` et `architecture/explication.md`.

`refactor` applique une cible : `hexagonal`, `tdd`, `hexa-tdd`, ou un texte libre (`--arch` / `--arch-file`). Sans `--apply`, les fichiers ne sont pas modifiés : l'agent enregistre seulement les diffs. `--apply` écrit sur le disque. Hors dépôt git, il faut aussi `--yes`.

`chat` parle à l'agent sur le projet. `/plan` arrête d'écrire, `/apply` écrit, `/quit` sort. `--resume` reprend la session.

`new` crée un dossier vide avec la structure demandée, en Python ou en Flutter. Choix : `hexagonal`, `tdd`, ou les deux.

`train` enregistre des exemples dans `training/examples.jsonl`. Aux prochains `suggest`, `refactor` et `chat`, les exemples les plus proches sont envoyés à l'agent Cursor.
