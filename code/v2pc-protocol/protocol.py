"""
Le due fasi del protocollo V2PC su un intero circuito.

Costruzione (Alice): dal filo di uscita agli ingressi, per ogni porta si
costruisce il VGESS e le share prodotte diventano le immagini dei fili di
ingresso. Al termine ogni filo di ingresso ha due trasparenze, una per valore.

Valutazione: dagli ingressi all'uscita, ogni porta sovrappone la share sinistra
alla meta' della destra indicata dal pointer bit, fino all'immagine di uscita.

Nota di modellazione: le immagini vengono ricostruite visualmente (il bianco
resta probabilistico, quindi gli errori si accumulano con il numero di porte del
circuito); il pointer bit e' invece esatto, come lo rende lo schema deterministico
(2,2)-NS.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from vc import value_image, read_value
from circuit import Input, Not, Circuit, gate_value
from vgess import build_gate, eval_gate


@dataclass
class Constructed:
    input_shares: dict
    bmap: dict
    circuit: Circuit
    size: int


def build(circuit: Circuit, size: int, rng: np.random.Generator) -> Constructed:
    i0, i1 = value_image(0, size), value_image(1, size)
    input_shares: dict = {}
    bmap: dict = {}

    def rec(node, img0, img1):
        if isinstance(node, Input):
            input_shares[id(node)] = {0: img0, 1: img1}
            return
        if isinstance(node, Not):
            rec(node.child, img1, img0)
            return
        left, right, b = build_gate(node.op, img0, img1, rng)
        bmap[id(node)] = b
        rec(node.left,  left[0][1], left[1][1])
        rec(node.right, right[0],   right[1])

    rec(circuit.root, i0, i1)
    return Constructed(input_shares, bmap, circuit, size)


def evaluate(cc: Constructed, assignment: dict) -> int:
    def rec(node):
        if isinstance(node, Input):
            v = assignment[node.name]
            return cc.input_shares[id(node)][v], v
        if isinstance(node, Not):
            child_img, w = rec(node.child)
            return child_img, 1 - w
        left_img, v1 = rec(node.left)
        right_img, v2 = rec(node.right)
        p = v1 ^ cc.bmap[id(node)]
        out_img = eval_gate((p, left_img), right_img)
        return out_img, gate_value(node.op, v1, v2)

    out_img, _ = rec(cc.circuit.root)
    return read_value(out_img)