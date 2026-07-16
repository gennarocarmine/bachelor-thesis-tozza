"""
Primitive di crittografia visuale per il protocollo V2PC.

Convenzione sulle immagini: sono matrici NumPy di 0 e 1, con 1 = pixel nero, 0 = pixel bianco (trasparente).
La sovrapposizione di due share (Sup) e' l'OR logico, esattamente come la sovrapposizione fisica di due trasparenze.
"""
from __future__ import annotations
import numpy as np


def image_zero(size: int) -> np.ndarray:
    return np.zeros((size, size), dtype=np.uint8)


def image_one(size: int) -> np.ndarray:
    return np.ones((size, size), dtype=np.uint8)


def value_image(bit: int, size: int) -> np.ndarray:
    if bit == 0:
        return image_zero(size)
    elif bit == 1:
        return image_one(size)
    else:
        raise ValueError("Il bit deve essere 0 o 1.")


def sup(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Sovrapposizione di due immagini (OR logico)."""
    return np.bitwise_or(a, b)


def kk_share(secret: np.ndarray, rng: np.random.Generator):
    """Schema random grid (2,2) di Kafri e Keren: due share di una singola immagine."""
    secret = np.asarray(secret, dtype=np.uint8)
    r1 = rng.integers(0, 2, size=secret.shape, dtype=np.uint8)
    r2 = np.where(secret == 0, r1, 1 - r1).astype(np.uint8)
    return r1, r2


def mvcs_share(i0: np.ndarray, i1: np.ndarray, rng: np.random.Generator):
    """Scheme-2-MVCS: tre share sh1, sh2, sh3 tali che Sup(sh1,sh2)=i0 e Sup(sh1,sh3)=i1."""
    i0 = np.asarray(i0, dtype=np.uint8)
    i1 = np.asarray(i1, dtype=np.uint8)
    if i0.shape != i1.shape:
        raise ValueError("Le immagini devono avere la stessa dimensione.")
    sh1 = rng.integers(0, 2, size=i0.shape, dtype=np.uint8)
    sh2 = np.where(i0 == 0, sh1, 1 - sh1).astype(np.uint8)
    sh3 = np.where(i1 == 0, sh1, 1 - sh1).astype(np.uint8)
    return sh1, sh2, sh3


def read_value(image: np.ndarray) -> int:
    return 1 if np.all(np.asarray(image) == 1) else 0