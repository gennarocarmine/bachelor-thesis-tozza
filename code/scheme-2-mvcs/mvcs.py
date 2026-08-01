"""Scheme-2-MVCS: random grid multi-secret visual cryptography scheme.

Porting in Python dello schema di D'Arco e De Prisco (TCS 651, 2016, Sez. 3.2).

Convenzione: 1 = pixel nero, 0 = pixel bianco (trasparente).
Le immagini sono array numpy di uint8 con valori in {0, 1}.
"""

import numpy as np
from PIL import Image

def shr(i0, i1, rng=None):
    """Condivide due segreti in tre share. (sh1,sh2) -> i0, (sh1,sh3) -> i1."""
    if i0.shape != i1.shape:
        raise ValueError("i due segreti devono avere la stessa dimensione")
    rng = np.random.default_rng() if rng is None else rng
    sh1 = rng.integers(0, 2, i0.shape, dtype=np.uint8)  # random grid
    return sh1, sh1 ^ i0, sh1 ^ i1


def sup(a, b):
    """Sovrapposizione di due share: OR logico, il nero copre il bianco."""
    return a | b


# --- generazione delle figure per la tesi ---

def _save(img, path, scale=12):
    """Salva un array {0,1} come PNG in bianco e nero, ingrandito di `scale`."""
    px = np.where(img == 1, 0, 255).astype(np.uint8)
    Image.fromarray(px, mode="L").resize(
        (px.shape[1] * scale, px.shape[0] * scale), Image.NEAREST
    ).save(path)


def _cerchio(h, w, r):
    y, x = np.ogrid[:h, :w]
    return ((y - h / 2 + .5) ** 2 + (x - w / 2 + .5) ** 2 <= r ** 2).astype(np.uint8)


def _croce(h, w, sp):
    y, x = np.ogrid[:h, :w]
    return ((abs(y - h / 2 + .5) < sp) | (abs(x - w / 2 + .5) < sp)).astype(np.uint8)


def demo(outdir=".", seed=7):
    rng = np.random.default_rng(seed)
    i0, i1 = _cerchio(48, 48, 17), _croce(48, 48, 6)
    sh1, sh2, sh3 = shr(i0, i1, rng)

    # controllo: il nero si ricostruisce sempre, il bianco a volte
    assert np.all(sup(sh1, sh2)[i0 == 1] == 1), "nero di I0 non esatto"
    assert np.all(sup(sh1, sh3)[i1 == 1] == 1), "nero di I1 non esatto"
    assert 0 < sup(sh1, sh2)[i0 == 0].mean() < 1, "bianco di I0 degenere"

    for nome, img in [("I0", i0), ("I1", i1), ("sh1", sh1), ("sh2", sh2),
                      ("sh3", sh3), ("sup_12", sup(sh1, sh2)),
                      ("sup_13", sup(sh1, sh3))]:
        _save(img, f"{outdir}/mvcs_{nome}.png")

    bianchi = 1 - sup(sh1, sh2)[i0 == 0].mean()
    print(f"aree bianche di I0 ricostruite bianche: {bianchi:.3f} (atteso ~0.5)")


if __name__ == "__main__":
    demo()