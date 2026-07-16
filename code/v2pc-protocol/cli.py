"""
Interfaccia a riga di comando per il protocollo V2PC.

La funzione booleana si scrive come espressione sulle variabili con gli
operatori & (AND), | (OR), ^ (XOR) e ~ (NOT), es. "(x1|y1) & ~(x2&y2)". Le porte
NAND, NOR e XNOR si ottengono come ~(a&b), ~(a|b), ~(a^b). Le variabili che
iniziano per x sono input di Alice, quelle che iniziano per y input di Bob.

Comandi:
  evaluate EXPR --input ...   valuta la funzione su un input dato
  shares   EXPR --input ...   salva le share stampabili usate per quell'input
  multi    EXPR ... --input   valuta una funzione a piu' uscite
"""
from __future__ import annotations
import argparse
import ast
import numpy as np

from circuit import input, AND, OR, XOR, NOT, Circuit
from protocol import build, evaluate
from render import save_share, save_used_shares, eval_image
from multi import build_multi, evaluate_multi


def parse_expr(expr: str) -> Circuit:
    def walk(node):
        if isinstance(node, ast.Name):
            return input(node.id)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Invert):
            return NOT(walk(node.operand))
        if isinstance(node, ast.BinOp):
            a, b = walk(node.left), walk(node.right)
            if isinstance(node.op, ast.BitAnd):
                return AND(a, b)
            if isinstance(node.op, ast.BitOr):
                return OR(a, b)
            if isinstance(node.op, ast.BitXor):
                return XOR(a, b)
        raise ValueError("usa variabili e gli operatori & (AND), | (OR), "
                         "^ (XOR), ~ (NOT), con le parentesi")
    return Circuit(walk(ast.parse(expr, mode="eval").body))


def parse_input(s: str) -> dict:
    """Da 'x1=0,y1=1,...' a un dizionario {nome: bit}."""
    coppie = [p.split("=") for p in s.split(",") if p]
    return {k.strip(): int(v) for k, v in coppie}


def cmd_evaluate(args):
    c = parse_expr(args.expr)
    asg = parse_input(args.input)
    cc = build(c, args.size, np.random.default_rng(args.seed))
    visuale = evaluate(cc, asg)
    vera = c.evaluate(asg)
    stato = "OK" if visuale == vera else "DISCORDANZA"
    print(f"funzione vera f = {vera}   uscita visuale = {visuale}   [{stato}]")


def cmd_shares(args):
    c = parse_expr(args.expr)
    asg = parse_input(args.input)
    cc = build(c, args.size, np.random.default_rng(args.seed))
    save_used_shares(cc, asg, args.out)
    save_share(eval_image(cc, asg), f"{args.out}/uscita.png")
    print(f"share e uscita salvate in: {args.out}/")


def cmd_multi(args):
    circuits = [parse_expr(e) for e in args.expr]
    asg = parse_input(args.input)
    ccs = build_multi(circuits, args.size, np.random.default_rng(args.seed))
    visuale = evaluate_multi(ccs, asg)
    vera = [c.evaluate(asg) for c in circuits]
    stato = "OK" if visuale == vera else "DISCORDANZA"
    print(f"funzione vera = {vera}   uscita visuale = {visuale}   [{stato}]")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Protocollo V2PC in Python.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("evaluate", help="valuta la funzione su un input")
    p.add_argument("expr")
    p.add_argument("--input", required=True, help="es. x1=0,y1=1,...")
    p.add_argument("--size", type=int, default=32)
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(func=cmd_evaluate)

    p = sub.add_parser("shares", help="salva le share stampabili di un input")
    p.add_argument("expr")
    p.add_argument("--input", required=True, help="es. x1=0,y1=1,...")
    p.add_argument("--size", type=int, default=32)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", default="share_v2pc")
    p.set_defaults(func=cmd_shares)

    p = sub.add_parser("multi", help="valuta una funzione a piu' uscite")
    p.add_argument("expr", nargs="+", help="un'espressione per ogni bit di uscita")
    p.add_argument("--input", required=True, help="es. x=0,y=1,...")
    p.add_argument("--size", type=int, default=32)
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(func=cmd_multi)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()