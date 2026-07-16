"""
Realizzazione visuale di una singola porta (VGESS).
 
Da due immagini I0, I1 associate al filo di uscita di una porta, costruisce le
share dei due fili di ingresso. La valutazione sovrappone la share sinistra
alla meta' della share destra indicata dal pointer bit p = v1 xor b.
"""
from __future__ import annotations
import numpy as np

from vc import mvcs_share, sup
from circuit import gate_value

def build_gate(op: str, i0: np.ndarray, i1: np.ndarray, rng: np.random.Generator):
    def out(a: int, c: int) -> np.ndarray:
        return i1 if gate_value(op, a, c) else i0
    
    sh1A, sh2A, sh3A = mvcs_share(out(0, 0), out(0, 1), rng)
    sh1B, sh2B, sh3B = mvcs_share(out(1, 0), out(1, 1), rng)

    b = int(rng.integers(0, 2))
            
    left = {0: (0 ^ b, sh1A), 1: (1 ^ b, sh1B)}

    A = {0: sh2A, 1: sh3A}
    B = {0: sh2B, 1: sh3B}

    if b == 0:
        right = {v2: np.hstack([A[v2], B[v2]]) for v2 in (0, 1)}
    else:
        right = {v2: np.hstack([B[v2], A[v2]]) for v2 in (0, 1)}
    
    return left, right, b

def eval_gate(left_share, right_share: np.ndarray) -> np.ndarray:
    p, sh1 = left_share
    w = right_share.shape[1] // 2
    half = right_share[:, :w] if p == 0 else right_share[:, w:]
    return sup(sh1, half)