from pathlib import Path

from clean_ia.scaffold.common import ensure_empty, project_name, write


def create_python_project(path: Path, styles: frozenset[str] | None = None) -> Path:
    root = path.resolve()
    name = project_name(root)
    chosen = styles or frozenset({"hexagonal"})
    ensure_empty(root)
    pkg = root / "src" / name
    write(root / "pyproject.toml", _pyproject(name))
    write(pkg / "__init__.py", "")
    if "hexagonal" in chosen:
        _write_hexagonal(pkg, name)
    else:
        write(pkg / "place_order.py", _flat_place_order())
    if "tdd" in chosen:
        write(root / "tests" / "test_place_order.py", _test(name, "hexagonal" in chosen))
    return root


def _write_hexagonal(pkg: Path, name: str) -> None:
    write(pkg / "domain" / "__init__.py", "")
    write(pkg / "domain" / "order.py", _order())
    write(pkg / "domain" / "order_repository.py", _port())
    write(pkg / "application" / "__init__.py", "")
    write(pkg / "application" / "place_order.py", _use_case(name))
    write(pkg / "infrastructure" / "__init__.py", "")
    write(pkg / "infrastructure" / "memory_order_repository.py", _adapter(name))
    write(pkg / "interfaces" / "__init__.py", "")
    write(pkg / "interfaces" / "cli.py", _cli(name))


def _pyproject(name: str) -> str:
    return (
        "[project]\n"
        f'name = "{name}"\n'
        'version = "0.1.0"\n'
        'requires-python = ">=3.11"\n'
        "\n"
        "[tool.setuptools.packages.find]\n"
        'where = ["src"]\n'
    )


def _order() -> str:
    return (
        "from dataclasses import dataclass\n"
        "\n"
        "\n"
        "@dataclass(frozen=True)\n"
        "class Order:\n"
        "    item: str\n"
        "    total: int\n"
    )


def _port() -> str:
    return (
        "from typing import Protocol\n"
        "\n"
        "from .order import Order\n"
        "\n"
        "\n"
        "class OrderRepository(Protocol):\n"
        "    def save(self, order: Order) -> None: ...\n"
    )


def _use_case(name: str) -> str:
    return (
        f"from {name}.domain.order import Order\n"
        f"from {name}.domain.order_repository import OrderRepository\n"
        "\n"
        "\n"
        "class PlaceOrder:\n"
        "    def __init__(self, repository: OrderRepository) -> None:\n"
        "        self._repository = repository\n"
        "\n"
        "    def execute(self, item: str, total: int) -> Order:\n"
        "        order = Order(item=item, total=total)\n"
        "        self._repository.save(order)\n"
        "        return order\n"
    )


def _adapter(name: str) -> str:
    return (
        f"from {name}.domain.order import Order\n"
        "\n"
        "\n"
        "class MemoryOrderRepository:\n"
        "    def __init__(self) -> None:\n"
        "        self.orders: list[Order] = []\n"
        "\n"
        "    def save(self, order: Order) -> None:\n"
        "        self.orders.append(order)\n"
    )


def _cli(name: str) -> str:
    return (
        f"from {name}.application.place_order import PlaceOrder\n"
        f"from {name}.infrastructure.memory_order_repository import MemoryOrderRepository\n"
        "\n"
        "\n"
        "def main() -> None:\n"
        "    order = PlaceOrder(MemoryOrderRepository()).execute('item', 1)\n"
        "    print(order.item)\n"
    )


def _flat_place_order() -> str:
    return (
        "class Order:\n"
        "    def __init__(self, item: str, total: int) -> None:\n"
        "        self.item = item\n"
        "        self.total = total\n"
        "\n"
        "\n"
        "def place_order(item: str, total: int) -> Order:\n"
        "    return Order(item, total)\n"
    )


def _test(name: str, hexagonal: bool) -> str:
    if not hexagonal:
        return (
            "import unittest\n"
            "\n"
            f"from {name}.place_order import place_order\n"
            "\n"
            "\n"
            "class PlaceOrderTests(unittest.TestCase):\n"
            "    def test_total_is_kept(self) -> None:\n"
            "        self.assertEqual(place_order('livre', 12).total, 12)\n"
        )
    return (
        "import unittest\n"
        "\n"
        f"from {name}.application.place_order import PlaceOrder\n"
        f"from {name}.infrastructure.memory_order_repository import MemoryOrderRepository\n"
        "\n"
        "\n"
        "class PlaceOrderTests(unittest.TestCase):\n"
        "    def test_total_is_kept(self) -> None:\n"
        "        repository = MemoryOrderRepository()\n"
        "        order = PlaceOrder(repository).execute('livre', 12)\n"
        "        self.assertEqual(order.total, 12)\n"
        "        self.assertEqual(repository.orders, [order])\n"
    )
