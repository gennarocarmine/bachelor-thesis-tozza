"""
Rappresentazione di una funzione booleana come circuito.
 
Un circuito e' un albero, come richiede il protocollo V2PC. Le foglie sono le
variabili di input (di Alice o di Bob); i nodi interni sono porte a due ingressi
(AND, OR, NAND, NOR, XOR, XNOR) oppure una negazione NOT; la radice e' la porta
di uscita. Una stessa variabile puo' comparire in piu' foglie, e ogni occorrenza
e' un filo distinto: cosi' si rappresentano anche le funzioni non read-once.
"""
from __future__ import annotations
from typing import Union
from dataclasses import dataclass

@dataclass(frozen=True)
class Input:
    name: str

@dataclass(frozen=True)
class Gate:
    op: str
    left: "Node"
    right: "Node"

@dataclass(frozen=True)
class Not:
    child: "Node"

Node = Union[Input, Gate, Not]

_OPS = {
    "AND":  lambda a, b: a & b,
    "OR":   lambda a, b: a | b,
    "NAND": lambda a, b: 1 - (a & b),
    "NOR":  lambda a, b: 1 - (a | b),
    "XOR":  lambda a, b: a ^ b,
    "XNOR": lambda a, b: 1 - (a ^ b),
}


def input(name: str) -> Input:
    return Input(name)
 
 
def AND(a: Node, b: Node) -> Gate:
    return Gate("AND", a, b)
 
 
def OR(a: Node, b: Node) -> Gate:
    return Gate("OR", a, b)
 
 
def NAND(a: Node, b: Node) -> Gate:
    return Gate("NAND", a, b)
 
 
def NOR(a: Node, b: Node) -> Gate:
    return Gate("NOR", a, b)
 
 
def XOR(a: Node, b: Node) -> Gate:
    return Gate("XOR", a, b)
 
 
def XNOR(a: Node, b: Node) -> Gate:
    return Gate("XNOR", a, b)
 
def NOT(a: Node) -> Not:
    return Not(a)

def gate_value(op: str, a: int, b: int) -> int:
    return _OPS[op](a, b)

def evaluate(node: Node, assignment: dict) -> int:
    if isinstance(node, Input):
        return assignment[node.name]
    if isinstance(node, Not):
        return 1 - evaluate(node.child, assignment)
    return gate_value(node.op, evaluate(node.left, assignment), evaluate(node.right, assignment))

def input_names(node: Node) -> list:
    ordinary = []
    def visit(n):
        if isinstance(n, Input):
            if n.name not in ordinary:
                ordinary.append(n.name)
        elif isinstance(n, Not):
            visit(n.child)
        else:
            visit(n.left)
            visit(n.right)
    visit(node)
    return ordinary

def input_leaves(node: Node) -> list:
    foglie = []
    def visita(n):
        if isinstance(n, Input):
            foglie.append(n)
        elif isinstance(n, Not):
            visita(n.child)
        else:
            visita(n.left)
            visita(n.right)
    visita(node)
    return foglie

def depth(node: Node) -> int:
    if isinstance(node, Input):
        return 0
    if isinstance(node, Not):
        return depth(node.child)
    return 1 + max(depth(node.left), depth(node.right))

@dataclass(frozen=True)
class Circuit:
    root: Node

    def evaluate(self, assignment: dict) -> int:
        return evaluate(self.root, assignment)
    
    @property
    def inputs(self) -> list:
        return input_names(self.root)
    
    @property
    def depth(self) -> int:
        return depth(self.root)