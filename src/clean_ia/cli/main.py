import argparse
import sys
from pathlib import Path

from clean_ia import __version__
from clean_ia.analyzer.service import ProjectAnalyzer, render_report
from clean_ia.audit.render import render_audit
from clean_ia.audit.service import run_audit, write_audit
from clean_ia.config import ConfigError, load_settings
from clean_ia.orchestrator.agent import Orchestrator
from clean_ia.orchestrator.heuristic import format_architecture
from clean_ia.training.dataset import add_example, load_examples
from clean_ia.scaffold import create_flutter_project, create_python_project
from clean_ia.scaffold.common import describe_styles, parse_styles


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="clean-ia",
        description="Analyse un projet et le refactorise vers une architecture.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="Scan, AST, dépendances, problèmes")
    analyze.add_argument("project")

    suggest = sub.add_parser("suggest", help="Propose une architecture")
    _add_project_args(suggest)

    refactor = sub.add_parser("refactor", help="Refactorise vers une architecture")
    _add_project_args(refactor)
    refactor.add_argument("--arch", help="Cible : hexagonal, tdd, hexa-tdd, ou un texte libre")
    refactor.add_argument("--arch-file", type=Path, help="Fichier décrivant l'architecture")
    refactor.add_argument("--apply", action="store_true", help="Écrit les fichiers")
    refactor.add_argument("--yes", action="store_true", help="Autorise l'écriture hors dépôt git")

    chat = sub.add_parser("chat", help="Conversation avec l'agent")
    _add_project_args(chat)
    chat.add_argument("--apply", action="store_true")
    chat.add_argument("--resume", action="store_true")

    train = sub.add_parser("train", help="Ajoute des exemples qui guident l'agent")
    train_sub = train.add_subparsers(dest="train_command", required=True)
    train_add = train_sub.add_parser("add", help="Ajoute un exemple instruction / réponse")
    train_add.add_argument("--instruction", required=True)
    train_add.add_argument("--output")
    train_add.add_argument("--output-file", type=Path)
    train_add.add_argument("--data", type=Path, help="Fichier JSONL, défaut training/examples.jsonl")
    train_list = train_sub.add_parser("list", help="Liste les exemples")
    train_list.add_argument("--data", type=Path)

    _add_audit_parser(sub)

    create = sub.add_parser("new", help="Crée un projet avec la structure d'architecture")
    create.add_argument("language", choices=["python", "flutter"])
    create.add_argument("path")
    create.add_argument(
        "--arch",
        default="hexagonal",
        help="hexagonal, tdd, ou les deux : hexagonal,tdd",
    )

    args = parser.parse_args(argv)
    try:
        if args.command == "analyze":
            return _analyze(Path(args.project))
        if args.command == "suggest":
            return _suggest(args)
        if args.command == "refactor":
            return _refactor(args)
        if args.command == "train":
            return _train(args)
        if args.command == "new":
            return _new(args)
        if args.command == "audit":
            return _audit(args)
        return _chat(args)
    except (ConfigError, FileNotFoundError, FileExistsError, OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1


def _new(args) -> int:
    styles = parse_styles(args.arch)
    root = Path(args.path)
    if args.language == "python":
        created = create_python_project(root, styles)
    else:
        created = create_flutter_project(root, styles)
    print(f"Projet {args.language} créé ({', '.join(sorted(styles))}) : {created}")
    return 0


def _add_audit_parser(sub) -> None:
    audit = sub.add_parser("audit", help="Audit clean code ou sécurité, et écrit un rapport")
    kinds = audit.add_subparsers(dest="audit_kind", required=True)
    clean = kinds.add_parser("clean-code", help="Rapport de clean code")
    security = kinds.add_parser("securite", aliases=["security"], help="Rapport de sécurité")
    for parser in (clean, security):
        parser.add_argument("project")
        parser.add_argument("--output", type=Path, help="Fichier du rapport, défaut audits/ dans le projet")


def _audit(args) -> int:
    audit = run_audit(Path(args.project), args.audit_kind)
    path = write_audit(audit, args.output)
    print(render_audit(audit))
    print(f"\nRapport : {path}")
    return 0


def _add_project_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("project")
    parser.add_argument("--model")
    parser.add_argument("--max-turns", type=int, default=24)


def _analyze(project: Path) -> int:
    report = ProjectAnalyzer(project).analyze()
    print(render_report(report))
    return 0


def _suggest(args) -> int:
    report = ProjectAnalyzer(Path(args.project)).analyze()
    print(render_report(report))
    print()
    agent = Orchestrator(report, load_settings(args.max_turns, args.model), apply=False, writes_enabled=False)
    result = agent.suggest()
    if not agent.settings.api_key:
        print(result.text)
    print("\narchitecture/modelisation.md")
    print("architecture/explication.md")
    for note in result.log.notes:
        print(note)
    return 0


def _refactor(args) -> int:
    root = Path(args.project).resolve()
    if args.apply and not args.yes and not (root / ".git").exists():
        print("Projet sans git. Relance avec --yes pour écrire quand même.", file=sys.stderr)
        return 1
    report = ProjectAnalyzer(root).analyze()
    print(render_report(report))
    print()
    target = _read_target(args)
    agent = Orchestrator(
        report,
        load_settings(args.max_turns, args.model),
        apply=args.apply,
        writes_enabled=True,
    )
    result = agent.refactor(target)
    _print_changes(result.log, args.apply)
    return 0


def _chat(args) -> int:
    root = Path(args.project).resolve()
    report = ProjectAnalyzer(root).analyze()
    print(render_report(report, limit=20))
    print("\nCommandes, après « Vous : » : /apply, /plan, /quit\n")
    agent = Orchestrator(
        report,
        load_settings(args.max_turns, args.model),
        apply=args.apply,
        writes_enabled=True,
    )
    resume = args.resume
    try:
        return _chat_loop(args, root, agent, resume)
    finally:
        agent.close()


def _chat_loop(args, root: Path, agent: Orchestrator, resume: bool) -> int:
    while True:
        try:
            message = input("Vous : ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if message in {"/quit", "quit", "exit"}:
            return 0
        if message == "/apply":
            if not args.yes and not (root / ".git").exists():
                print("Écriture refusée hors git. Relance avec --yes.")
                continue
            agent.apply = True
            print("Écriture activée.")
            continue
        if message == "/plan":
            agent.apply = False
            print("Mode plan.")
            continue
        if not message:
            continue
        try:
            agent.chat(message, resume=resume)
        except ConfigError as exc:
            print(exc)
            continue
        except Exception as exc:
            print(f"Erreur Cursor : {exc}")
            continue
        resume = False
        _print_changes(agent.log, agent.apply)


def _read_target(args) -> str | None:
    if getattr(args, "arch_file", None):
        return args.arch_file.read_text(encoding="utf-8")
    raw = getattr(args, "arch", None)
    if not raw:
        return None
    try:
        return describe_styles(parse_styles(raw))
    except ValueError:
        return raw.strip()


def _print_changes(log, apply: bool) -> None:
    if log.architecture:
        print("\n" + format_architecture(log.architecture))
    if not log.changes:
        return
    label = "Fichiers écrits" if apply else "Modifications proposées"
    print(f"\n{label} :")
    for change in log.changes:
        print(f"- {change.path}")
    if apply:
        return
    print("\nRelance avec --apply pour écrire ces fichiers.")


def _train(args) -> int:
    if args.train_command == "list":
        examples = load_examples(args.data)
        if not examples:
            print("Aucun exemple. Ajoute-en avec : clean-ia train add --instruction \"...\" --output \"...\"")
            return 0
        for number, item in enumerate(examples, start=1):
            print(f"{number}. {item.instruction[:120]}")
        print(f"\n{len(examples)} exemple(s).")
        return 0
    output = args.output
    if args.output_file:
        output = args.output_file.read_text(encoding="utf-8")
    if not output:
        print("Donne --output ou --output-file.", file=sys.stderr)
        return 1
    path = add_example(args.instruction, output, args.data)
    print(f"Exemple ajouté dans {path} ({len(load_examples(path))} au total).")
    return 0

