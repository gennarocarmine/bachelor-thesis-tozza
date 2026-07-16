"""
Funzioni booleane a piu' bit di uscita.

Una funzione f: {0,1}^n x {0,1}^n -> {0,1}^m si gestisce, come suggerito da
D'Arco e De Prisco, applicando la costruzione a ogni bit di uscita in modo
indipendente: si costruisce un circuito per ogni uscita e si valutano tutti sullo
stesso input.
"""
from __future__ import annotations
import numpy as np

from protocol import build, evaluate


def build_multi(circuits: list, size: int, rng: np.random.Generator) -> list:
    return [build(c, size, rng) for c in circuits]


def evaluate_multi(constructions: list, assignment: dict) -> list:
    return [evaluate(cc, assignment) for cc in constructions]