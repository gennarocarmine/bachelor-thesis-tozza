"""
Salvataggio delle share come immagini stampabili e riproduzione
di un'esecuzione del protocollo.

Ogni share e' una matrice 0/1 (1 = nero). La si salva come PNG ingrandita, cosi'
da poterla stampare su lucido e sovrapporre fisicamente.
"""
from __future__ import annotations
import os
import numpy as np
from PIL import Image
from collections import Counter

from circuit import Input, Not, gate_value, input_leaves
from vgess import eval_gate
from protocol import Constructed


def save_share(image: np.ndarray, path: str, scale: int = 8):
    img = Image.fromarray(np.where(np.asarray(image) == 1, 0, 255).astype(np.uint8), mode="L")
    img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    img.save(path)


def eval_image(cc, assignment):
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
        return eval_gate((p, left_img), right_img), gate_value(node.op, v1, v2)
    return rec(cc.circuit.root)[0]


def _wire_labels(foglie: list) -> list:
    conteggio = Counter(l.name for l in foglie)
    visti: Counter = Counter()
    etichette = []
    for l in foglie:
        if conteggio[l.name] > 1:
            visti[l.name] += 1
            etichette.append(f"{l.name}_{visti[l.name]}")
        else:
            etichette.append(l.name)
    return etichette


def save_used_shares(cc: Constructed, assignment: dict, out_dir: str, scale: int = 8) -> None:
    os.makedirs(out_dir, exist_ok=True)
    foglie = input_leaves(cc.circuit.root)
    for leaf, et in zip(foglie, _wire_labels(foglie)):
        save_share(cc.input_shares[id(leaf)][assignment[leaf.name]],
                   f"{out_dir}/{et}.png", scale)