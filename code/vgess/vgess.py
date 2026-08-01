"""VGESS: visual gate evaluation secret sharing.

Istanziazione della meta-costruzione GenGESS (D'Arco e De Prisco, TCS 651, 2016,
Tab. 1) con lo Scheme-2-MVCS di mvcs.py. Realizza una singola porta booleana.

Convenzione ereditata da mvcs.py: 1 = nero, 0 = bianco.
Il pointer bit e' scritto nella forma ricostruita dello schema (2,2)-NS:
due sotto-pixel, [bianco nero] per 0 e [nero nero] per 1.
"""

import sys, pathlib
import numpy as np

MVCS_DIR = pathlib.Path(__file__).resolve().parent.parent / "scheme-2-mvcs"
sys.path.append(str(MVCS_DIR))
import mvcs

GATES = {
    "and": lambda a, b: a & b,
    "or": lambda a, b: a | b,
    "xor": lambda a, b: a ^ b,
    "nand": lambda a, b: 1 - (a & b),
}


def _pointer(bit, h):
    """Striscia 2 pixel del pointer bit, forma ricostruita (2,2)-NS."""
    return np.tile(np.array([bit, 1], dtype=np.uint8), (h, 1))


def shr_gate(gate, i0, i1, rng=None, b=None):
    """Condivide le immagini del filo di uscita sui due fili di ingresso.

    Restituisce ((sx_0, sx_1), (dx_0, dx_1)): due share per filo, una per valore.
    """
    g = GATES[gate] if isinstance(gate, str) else gate
    rng = np.random.default_rng() if rng is None else rng
    b = int(rng.integers(0, 2)) if b is None else b
    img = {0: i0, 1: i1}
    h = i0.shape[0]

    # istanza A: filo sinistro a 0; istanza B: filo sinistro a 1
    a1, a2, a3 = mvcs.shr(img[g(0, 0)], img[g(0, 1)], rng)
    b1, b2, b3 = mvcs.shr(img[g(1, 0)], img[g(1, 1)], rng)

    sx = (np.hstack([_pointer(b, h), a1]),
          np.hstack([_pointer(1 - b, h), b1]))
    # il bit di permutazione decide l'ordine delle due meta' sul filo destro
    order = (lambda u, v: (u, v)) if b == 0 else (lambda u, v: (v, u))
    dx = (np.hstack(order(a2, b2)), np.hstack(order(a3, b3)))
    return sx, dx


def rec(sx, dx):
    """Valuta la porta: legge il pointer bit, ritaglia la meta' giusta, sovrappone."""
    p = int(sx[0, 0])                 # primo sotto-pixel: nero = 1, bianco = 0
    sh1 = sx[:, 2:]                   # il resto della share sinistra
    w = dx.shape[1] // 2
    return mvcs.sup(sh1, dx[:, :w] if p == 0 else dx[:, w:])


# --- generazione delle figure per la tesi ---------------------------------

def _check(gate, i0, i1, rng):
    """Correttezza su tutte le combinazioni di ingresso e di bit di permutazione."""
    g = GATES[gate]
    for b in (0, 1):
        sx, dx = shr_gate(gate, i0, i1, rng, b=b)
        for v1 in (0, 1):
            for v2 in (0, 1):
                atteso = {0: i0, 1: i1}[g(v1, v2)]
                out = rec(sx[v1], dx[v2])
                assert np.all(out[atteso == 1] == 1), \
                    f"{gate}: nero non esatto per b={b}, v=({v1},{v2})"


def demo(outdir=".", gate="and", seed=11):
    rng = np.random.default_rng(seed)
    i0, i1 = mvcs._cerchio(48, 48, 17), mvcs._croce(48, 48, 6)
    _check(gate, i0, i1, rng)

    sx, dx = shr_gate(gate, i0, i1, rng, b=0)
    for v in (0, 1):
        mvcs._save(sx[v], f"{outdir}/vgess_sx_{v}.png")
        mvcs._save(dx[v], f"{outdir}/vgess_dx_{v}.png")
    for v1 in (0, 1):
        for v2 in (0, 1):
            mvcs._save(rec(sx[v1], dx[v2]), f"{outdir}/vgess_sup_{v1}{v2}.png")
            print(f"({v1},{v2}) -> {GATES[gate](v1, v2)}")


if __name__ == "__main__":
    demo()