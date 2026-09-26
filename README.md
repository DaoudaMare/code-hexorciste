# hexorciste

Agent Python qui exorcise les god objects et range le code en couches.

Analyse un projet, chasse les smells, et le refactorise vers l'architecture hexagonale — ou celle que tu imposes. La commande s'appelle `clean-ia`.

```
CLI
 └─ Orchestrateur
     ├─ Analyseur (scan, AST, dépendances)
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

`CURSOR_API_KEY` est nécessaire pour `suggest`, `refactor` et `chat`. Le modèle par défaut est `composer-2.5`. `analyze` et `audit` fonctionnent sans clé.

## Usage

```bash
clean-ia analyze ./mon-projet
clean-ia audit clean-code ./mon-projet
clean-ia audit securite ./mon-projet
clean-ia suggest ./mon-projet
clean-ia refactor ./mon-projet --arch-file archi.txt
clean-ia refactor ./mon-projet --arch "hexagonal, domain / application / infrastructure" --apply
clean-ia chat ./mon-projet
clean-ia new python ./mon-projet --arch hexagonal,tdd
clean-ia new flutter ./mon-app --arch hexagonal
clean-ia train add --instruction "Découpe ce fichier god object en couches." --output "Domain sans framework, application pour les cas d'usage, infrastructure pour le disque."
clean-ia train list
```

`audit` écrit `audits/clean-code.md` ou `audits/securite.md` dans le projet.

`new` crée un projet Python ou Flutter déjà rangé (`hexagonal`, `tdd`, ou les deux).

`train` enregistre des exemples dans `training/examples.jsonl`. Aux prochains `suggest`, `refactor` et `chat`, les exemples les plus proches sont envoyés à l'agent Cursor.

Sans `--apply`, les fichiers ne sont pas modifiés : l'agent enregistre seulement les diffs. `--apply` écrit sur le disque. Hors dépôt git, il faut aussi `--yes`.

Dans `chat` : `/plan` pour arrêter d'écrire, `/apply` pour écrire, `/quit` pour sortir.
