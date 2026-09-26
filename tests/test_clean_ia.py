import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from clean_ia.analyzer.service import ProjectAnalyzer
from clean_ia.index.store import CodeIndex
from clean_ia.models import RunLog
from clean_ia.tools.registry import ToolContext, execute


class AnalyzerTests(unittest.TestCase):
    def test_finds_smells_and_cycles(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "a.py").write_text(
                "import b\n" + "\n".join(f"x{i} = {i}" for i in range(50)) + "\n\ndef run():\n" + "    pass\n" * 45,
                encoding="utf-8",
            )
            (root / "b.py").write_text("import a\n\ndef other():\n    return 1\n", encoding="utf-8")
            report = ProjectAnalyzer(root).analyze()
            codes = {smell.code for smell in report.smells}
            self.assertIn("function-too-long", codes)
            self.assertTrue(report.cycles)
            self.assertEqual(report.languages["python"], 2)


class IndexTests(unittest.TestCase):
    def test_search_finds_symbol(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "billing.py").write_text(
                "def compute_invoice_total(amount):\n    return amount * 2\n",
                encoding="utf-8",
            )
            report = ProjectAnalyzer(root).analyze()
            index = CodeIndex()
            index.build(report)
            hits = index.search("invoice total")
            self.assertTrue(hits)
            self.assertEqual(hits[0].path, "billing.py")


class ScaffoldTests(unittest.TestCase):
    def test_python_and_flutter_keep_domain_free_of_frameworks(self) -> None:
        from clean_ia.scaffold import create_python_project
        from clean_ia.scaffold.flutter_app import _write_architecture, flutter_create_command

        with TemporaryDirectory() as raw:
            root = Path(raw)
            python_root = create_python_project(root / "billing")
            flutter_root = root / "billing_app"
            flutter_root.mkdir()
            (flutter_root / "pubspec.yaml").write_text("name: billing_app\n", encoding="utf-8")
            _write_architecture(flutter_root, "billing_app", frozenset({"hexagonal", "tdd"}))
            domain_py = (python_root / "src" / "billing" / "domain" / "order_repository.py").read_text(encoding="utf-8")
            domain_dart = (flutter_root / "lib" / "domain" / "order_repository.dart").read_text(encoding="utf-8")
            self.assertTrue((python_root / "src" / "billing" / "domain").is_dir())
            self.assertFalse((python_root / "tests" / "test_place_order.py").exists())
            combo = create_python_project(root / "combo", frozenset({"hexagonal", "tdd"}))
            self.assertTrue((combo / "tests" / "test_place_order.py").is_file())
            self.assertTrue((combo / "src" / "combo" / "domain" / "order_repository.py").is_file())
            self.assertNotIn("sqlalchemy", domain_py)
            self.assertIn("abstract interface class", domain_dart)
            self.assertNotIn("package:flutter", domain_dart)
            self.assertTrue((flutter_root / "test" / "place_order_test.dart").is_file())
            command = flutter_create_command(flutter_root, "billing_app")
            self.assertEqual(command[:3], ["flutter", "create", "--project-name"])
            self.assertEqual(command[3], "billing_app")


class StyleTests(unittest.TestCase):
    def test_hexa_tdd_alias_describes_both(self) -> None:
        from clean_ia.scaffold.common import describe_styles, parse_styles

        styles = parse_styles("hexa-tdd")
        text = describe_styles(styles)
        self.assertEqual(styles, frozenset({"hexagonal", "tdd"}))
        self.assertIn("domain", text)
        self.assertIn("test", text.lower())


class InventoryTests(unittest.TestCase):
    def test_flags_function_never_called(self) -> None:
        from clean_ia.orchestrator.inventory import _unused_symbols

        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "app.py").write_text("def used():\n    return 1\n\ndef orphan():\n    return 2\n\nused()\n", encoding="utf-8")
            report = ProjectAnalyzer(root).analyze()
            unused = _unused_symbols(report)
            self.assertIn("app.py:orphan", unused)
            self.assertNotIn("app.py:used", unused)


class ArchitectureDocTests(unittest.TestCase):
    def test_suggest_writes_two_markdown_files(self) -> None:
        from clean_ia.orchestrator.architecture_docs import ensure_architecture_docs

        with TemporaryDirectory() as raw:
            root = Path(raw)
            plan = {
                "summary": "12 fichiers, 2 problèmes.",
                "layers": [
                    {"name": "domain", "responsibility": "Métier.", "target_paths": ["src/domain"]},
                    {"name": "interfaces", "responsibility": "CLI.", "target_paths": ["src/interfaces"]},
                ],
                "steps": [],
            }
            ensure_architecture_docs(root, plan, "Découpage proposé.")
            model = (root / "architecture" / "modelisation.md").read_text(encoding="utf-8")
            explain = (root / "architecture" / "explication.md").read_text(encoding="utf-8")
            self.assertIn("mermaid", model)
            self.assertIn("domain", model)
            self.assertIn("Avantages", explain)
            self.assertIn("Inconvénients", explain)


class TrainingTests(unittest.TestCase):
    def test_add_and_retrieve_example(self) -> None:
        from clean_ia.training.dataset import add_example, load_examples, relevant_examples

        with TemporaryDirectory() as raw:
            path = Path(raw) / "examples.jsonl"
            add_example("séparer la facturation en couches", "domain/invoice.py sans framework", path)
            add_example("renommer les tests", "garder pytest et des noms explicites", path)
            examples = load_examples(path)
            self.assertEqual(len(examples), 2)
            hit = relevant_examples("architecture facturation", examples, limit=1)
            self.assertIn("facturation", hit[0].instruction)


class AuditTests(unittest.TestCase):
    def test_clean_code_audit_reports_long_function_and_cycle(self) -> None:
        from clean_ia.audit.service import run_audit
        from clean_ia.audit.render import render_audit

        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "a.py").write_text(
                "import b\n" + "\n".join(f"x{i} = {i}" for i in range(50)) + "\n\ndef run():\n" + "    pass\n" * 45,
                encoding="utf-8",
            )
            (root / "b.py").write_text("import a\n\ndef other():\n    return 1\n", encoding="utf-8")
            audit = run_audit(root, "clean-code")
            codes = {item.code for item in audit.findings}
            self.assertIn("function-too-long", codes)
            self.assertIn("import-cycle", codes)
            text = render_audit(audit)
            self.assertIn("Audit clean code", text)
            self.assertIn("Recommandation", text)
            self.assertIn("a.py", text)

    def test_security_audit_flags_secret_without_leaking_it(self) -> None:
        from clean_ia.audit.service import run_audit, write_audit
        from clean_ia.audit.render import render_audit

        secret = "s3cr3t-valeur-demo"
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "app.py").write_text(
                f'password = "{secret}"\n'
                'token = os.environ["TOKEN"]\n'
                "import subprocess\n"
                "subprocess.run(cmd, shell=True)\n",
                encoding="utf-8",
            )
            audit = run_audit(root, "securite")
            codes = {item.code for item in audit.findings}
            self.assertIn("hardcoded-secret", codes)
            self.assertIn("shell-true", codes)
            text = render_audit(audit)
            self.assertNotIn(secret, text)
            self.assertNotIn("TOKEN", text)
            path = write_audit(audit)
            self.assertEqual(path, root.resolve() / "audits" / "securite.md")
            self.assertNotIn(secret, path.read_text(encoding="utf-8"))

    def test_cli_audit_writes_report(self) -> None:
        from clean_ia.cli.main import main

        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "app.py").write_text("def add(left, right):\n    return left + right\n", encoding="utf-8")
            with redirect_stdout(StringIO()):
                code = main(["audit", "clean-code", str(root)])
            self.assertEqual(code, 0)
            self.assertTrue((root / "audits" / "clean-code.md").is_file())


class ToolTests(unittest.TestCase):
    def test_write_stays_inside_project_and_can_plan(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            context = ToolContext(
                root=root,
                log=RunLog(),
                index=CodeIndex(),
                apply=False,
                writes_enabled=True,
            )
            preview = execute("write_file", {"path": "src/app.py", "content": "x = 1\n"}, context)
            self.assertIn("proposé", preview)
            self.assertFalse((root / "src" / "app.py").exists())
            self.assertEqual(len(context.log.changes), 1)
            refused = execute("write_file", {"path": "../secret.py", "content": "nope"}, context)
            self.assertIn("Erreur", refused)
            self.assertEqual(len(context.log.changes), 1)

    def test_apply_writes_file(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            context = ToolContext(
                root=root,
                log=RunLog(),
                index=CodeIndex(),
                apply=True,
                writes_enabled=True,
            )
            execute("write_file", {"path": "src/app.py", "content": "x = 1\n"}, context)
            self.assertEqual((root / "src" / "app.py").read_text(encoding="utf-8"), "x = 1\n")


if __name__ == "__main__":
    unittest.main()
