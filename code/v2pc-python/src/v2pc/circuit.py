"""Rappresentazione e parsing sicuro di formule booleane."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Iterator, Union


@dataclass(frozen=True)
class Input:
    name: str


@dataclass(frozen=True)
class Gate:
    operation: str
    left: "Node"
    right: "Node"


@dataclass(frozen=True)
class Not:
    child: "Node"


Node = Union[Input, Gate, Not]

_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_BINARY_AST = {
    ast.BitAnd: "AND",
    ast.BitOr: "OR",
    ast.BitXor: "XOR",
}
_OPERATIONS = {
    "AND": lambda a, b: a & b,
    "OR": lambda a, b: a | b,
    "XOR": lambda a, b: a ^ b,
}


def apply_gate(operation: str, left: int, right: int) -> int:
    try:
        function = _OPERATIONS[operation]
    except KeyError as exc:
        raise ValueError(f"Porta non supportata: {operation}") from exc
    return int(function(int(left), int(right)))


def _parse(node: ast.AST) -> Node:
    if isinstance(node, ast.Name) and _NAME.fullmatch(node.id):
        return Input(node.id)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Invert):
        return Not(_parse(node.operand))
    if isinstance(node, ast.BinOp):
        operation = _BINARY_AST.get(type(node.op))
        if operation is not None:
            return Gate(operation, _parse(node.left), _parse(node.right))
    raise ValueError(
        "Espressione non valida: usare nomi di variabile, parentesi e gli "
        "operatori & (AND), | (OR), ^ (XOR), ~ (NOT)."
    )


def parse_expression(expression: str) -> "Circuit":
    """Converte un'espressione in una formula senza eseguire codice Python."""
    if not expression or len(expression) > 2000:
        raise ValueError("L'espressione deve contenere da 1 a 2000 caratteri.")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Espressione non valida: {exc.msg}.") from exc
    return Circuit(expression=expression, root=_parse(tree.body))


def iter_leaves(node: Node) -> Iterator[Input]:
    if isinstance(node, Input):
        yield node
    elif isinstance(node, Not):
        yield from iter_leaves(node.child)
    else:
        yield from iter_leaves(node.left)
        yield from iter_leaves(node.right)


def iter_gates_postorder(node: Node) -> Iterator[Gate]:
    if isinstance(node, Input):
        return
    if isinstance(node, Not):
        yield from iter_gates_postorder(node.child)
        return
    yield from iter_gates_postorder(node.left)
    yield from iter_gates_postorder(node.right)
    yield node


def evaluate_node(node: Node, assignment: dict[str, int]) -> int:
    if isinstance(node, Input):
        try:
            value = int(assignment[node.name])
        except KeyError as exc:
            raise ValueError(f"Manca il valore di {node.name}.") from exc
        if value not in (0, 1):
            raise ValueError(f"{node.name} deve valere 0 oppure 1.")
        return value
    if isinstance(node, Not):
        return 1 - evaluate_node(node.child, assignment)
    return apply_gate(
        node.operation,
        evaluate_node(node.left, assignment),
        evaluate_node(node.right, assignment),
    )


def _depth(node: Node) -> int:
    if isinstance(node, Input):
        return 0
    if isinstance(node, Not):
        return _depth(node.child)
    return 1 + max(_depth(node.left), _depth(node.right))


@dataclass(frozen=True)
class Circuit:
    expression: str
    root: Node

    @property
    def variables(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(leaf.name for leaf in iter_leaves(self.root)))

    @property
    def leaf_names(self) -> tuple[str, ...]:
        return tuple(leaf.name for leaf in iter_leaves(self.root))

    @property
    def gate_count(self) -> int:
        return sum(1 for _ in iter_gates_postorder(self.root))

    @property
    def depth(self) -> int:
        return _depth(self.root)

    def evaluate(self, assignment: dict[str, int]) -> int:
        validate_assignment(self, assignment)
        return evaluate_node(self.root, assignment)


def validate_assignment(circuit: Circuit, assignment: dict[str, int]) -> None:
    missing = sorted(set(circuit.variables) - set(assignment))
    extra = sorted(set(assignment) - set(circuit.variables))
    if missing:
        raise ValueError(f"Valori mancanti: {', '.join(missing)}.")
    if extra:
        raise ValueError(f"Variabili non presenti nella funzione: {', '.join(extra)}.")
    invalid = sorted(name for name, value in assignment.items() if int(value) not in (0, 1))
    if invalid:
        raise ValueError(f"Valori diversi da 0 e 1: {', '.join(invalid)}.")
