import shutil
import subprocess
from pathlib import Path

from clean_ia.scaffold.common import project_name, write


def create_flutter_project(path: Path, styles: frozenset[str] | None = None) -> Path:
    root = path.resolve()
    name = project_name(root)
    chosen = styles or frozenset({"hexagonal"})
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"Le dossier n'est pas vide : {root}")
    _run_flutter_create(root, name)
    package = _package_name(root)
    _write_architecture(root, package, chosen)
    return root


def flutter_create_command(root: Path, name: str) -> list[str]:
    return ["flutter", "create", "--project-name", name, str(root)]


def _run_flutter_create(root: Path, name: str) -> None:
    command = flutter_create_command(root, name)
    binary = shutil.which("flutter")
    if binary is None:
        raise FileNotFoundError("La commande flutter est introuvable. Installe Flutter et réessaie.")
    command[0] = binary
    completed = subprocess.run(
        flutter_create_command(root, name),
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise OSError(detail or "flutter create a échoué.")


def _package_name(root: Path) -> str:
    for line in (root / "pubspec.yaml").read_text(encoding="utf-8").splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip()
    raise OSError("flutter create n'a pas écrit de pubspec.yaml.")


def _write_architecture(root: Path, name: str, styles: frozenset[str]) -> None:
    if "hexagonal" in styles:
        write(root / "lib" / "domain" / "order.dart", _order())
        write(root / "lib" / "domain" / "order_repository.dart", _port())
        write(root / "lib" / "application" / "place_order.dart", _use_case(name))
        write(root / "lib" / "infrastructure" / "memory_order_repository.dart", _adapter(name))
        write(root / "lib" / "interfaces" / "app.dart", _ui(name))
        write(root / "lib" / "main.dart", _main(name))
    else:
        write(root / "lib" / "place_order.dart", _flat_order())
        write(root / "lib" / "main.dart", _flat_main(name))
    if "tdd" in styles:
        write(root / "test" / "place_order_test.dart", _test(name, "hexagonal" in styles))
    widget_test = root / "test" / "widget_test.dart"
    if widget_test.is_file():
        widget_test.unlink()


def _order() -> str:
    return (
        "class Order {\n"
        "  const Order({required this.item, required this.total});\n"
        "\n"
        "  final String item;\n"
        "  final int total;\n"
        "}\n"
    )


def _port() -> str:
    return (
        "import 'order.dart';\n"
        "\n"
        "abstract interface class OrderRepository {\n"
        "  void save(Order order);\n"
        "}\n"
    )


def _use_case(name: str) -> str:
    return (
        f"import 'package:{name}/domain/order.dart';\n"
        f"import 'package:{name}/domain/order_repository.dart';\n"
        "\n"
        "class PlaceOrder {\n"
        "  const PlaceOrder(this._repository);\n"
        "\n"
        "  final OrderRepository _repository;\n"
        "\n"
        "  Order execute(String item, int total) {\n"
        "    final order = Order(item: item, total: total);\n"
        "    _repository.save(order);\n"
        "    return order;\n"
        "  }\n"
        "}\n"
    )


def _adapter(name: str) -> str:
    return (
        f"import 'package:{name}/domain/order.dart';\n"
        f"import 'package:{name}/domain/order_repository.dart';\n"
        "\n"
        "class MemoryOrderRepository implements OrderRepository {\n"
        "  final List<Order> orders = [];\n"
        "\n"
        "  @override\n"
        "  void save(Order order) {\n"
        "    orders.add(order);\n"
        "  }\n"
        "}\n"
    )


def _ui(name: str) -> str:
    return (
        "import 'package:flutter/material.dart';\n"
        "\n"
        f"import 'package:{name}/application/place_order.dart';\n"
        f"import 'package:{name}/infrastructure/memory_order_repository.dart';\n"
        "\n"
        "class OrderApp extends StatelessWidget {\n"
        "  const OrderApp({super.key});\n"
        "\n"
        "  @override\n"
        "  Widget build(BuildContext context) {\n"
        "    final order = PlaceOrder(MemoryOrderRepository()).execute('livre', 12);\n"
        "    return MaterialApp(home: Scaffold(body: Text(order.item)));\n"
        "  }\n"
        "}\n"
    )


def _main(name: str) -> str:
    return (
        "import 'package:flutter/widgets.dart';\n"
        "\n"
        f"import 'package:{name}/interfaces/app.dart';\n"
        "\n"
        "void main() {\n"
        "  runApp(const OrderApp());\n"
        "}\n"
    )


def _flat_order() -> str:
    return (
        "class Order {\n"
        "  const Order({required this.item, required this.total});\n"
        "\n"
        "  final String item;\n"
        "  final int total;\n"
        "}\n"
        "\n"
        "Order placeOrder(String item, int total) {\n"
        "  return Order(item: item, total: total);\n"
        "}\n"
    )


def _flat_main(name: str) -> str:
    return (
        "import 'package:flutter/widgets.dart';\n"
        "\n"
        f"import 'package:{name}/place_order.dart';\n"
        "\n"
        "void main() {\n"
        "  final order = placeOrder('livre', 12);\n"
        "  runApp(Directionality(textDirection: TextDirection.ltr, child: Text(order.item)));\n"
        "}\n"
    )


def _test(name: str, hexagonal: bool) -> str:
    if not hexagonal:
        return (
            "import 'package:flutter_test/flutter_test.dart';\n"
            f"import 'package:{name}/place_order.dart';\n"
            "\n"
            "void main() {\n"
            "  test('le total est conserve', () {\n"
            "    expect(placeOrder('livre', 12).total, 12);\n"
            "  });\n"
            "}\n"
        )
    return (
        "import 'package:flutter_test/flutter_test.dart';\n"
        f"import 'package:{name}/application/place_order.dart';\n"
        f"import 'package:{name}/infrastructure/memory_order_repository.dart';\n"
        "\n"
        "void main() {\n"
        "  test('le total est conserve', () {\n"
        "    final repository = MemoryOrderRepository();\n"
        "    final order = PlaceOrder(repository).execute('livre', 12);\n"
        "    expect(order.total, 12);\n"
        "    expect(repository.orders, [order]);\n"
        "  });\n"
        "}\n"
    )
