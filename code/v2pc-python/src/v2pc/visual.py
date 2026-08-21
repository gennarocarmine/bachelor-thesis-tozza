"""Primitive di crittografia visuale su matrici binarie."""

from __future__ import annotations

from typing import Iterable

import numpy as np
from numpy.typing import NDArray

BinaryImage = NDArray[np.uint8]


def _binary(data: np.ndarray | Iterable[int], *, dimensions: int | None = None) -> BinaryImage:
    result = np.asarray(data, dtype=np.uint8)
    if dimensions is not None and result.ndim != dimensions:
        raise ValueError(f"Attese {dimensions} dimensioni, ricevute {result.ndim}.")
    if result.size and np.any((result != 0) & (result != 1)):
        raise ValueError("Le immagini e le share possono contenere soltanto 0 e 1.")
    return result


def value_image(value: int, side: int) -> BinaryImage:
    if value not in (0, 1):
        raise ValueError("Il valore deve essere 0 oppure 1.")
    if side < 1 or side > 512:
        raise ValueError("Il lato dell'immagine deve essere compreso tra 1 e 512.")
    return np.full((side, side), value, dtype=np.uint8)


def overlay(left: np.ndarray, right: np.ndarray) -> BinaryImage:
    left_image = _binary(left, dimensions=2)
    right_image = _binary(right, dimensions=2)
    if left_image.shape != right_image.shape:
        raise ValueError(
            f"Share non allineabili: {left_image.shape} e {right_image.shape}."
        )
    return np.bitwise_or(left_image, right_image)


def read_value(image: np.ndarray) -> int:
    """Nero pieno vale 1; la presenza di almeno un pixel bianco vale 0."""
    checked = _binary(image, dimensions=2)
    return int(bool(checked.size) and np.all(checked == 1))


def random_grid_share(secret: np.ndarray, rng: np.random.Generator) -> tuple[BinaryImage, BinaryImage]:
    """Schema random grid (2,2) di Kafri e Keren."""
    checked = _binary(secret, dimensions=2)
    first = rng.integers(0, 2, size=checked.shape, dtype=np.uint8)
    second = np.bitwise_xor(first, checked)
    return first, second


def multi_secret_share(
    first_secret: np.ndarray,
    second_secret: np.ndarray,
    rng: np.random.Generator,
) -> tuple[BinaryImage, BinaryImage, BinaryImage]:
    """Scheme-2-MVCS: la prima share è comune alle due ricostruzioni."""
    first = _binary(first_secret, dimensions=2)
    second = _binary(second_secret, dimensions=2)
    if first.shape != second.shape:
        raise ValueError("I due segreti devono avere la stessa forma.")
    common = rng.integers(0, 2, size=first.shape, dtype=np.uint8)
    return common, np.bitwise_xor(common, first), np.bitwise_xor(common, second)


def deterministic_left(bit_count: int, rng: np.random.Generator) -> BinaryImage:
    """Share sinistra dello schema deterministico (2,2), due sotto-pixel per bit."""
    if bit_count < 0:
        raise ValueError("Il numero di bit non può essere negativo.")
    first_pixels = rng.integers(0, 2, size=bit_count, dtype=np.uint8)
    result = np.empty(2 * bit_count, dtype=np.uint8)
    result[0::2] = first_pixels
    result[1::2] = 1 - first_pixels
    return result


def deterministic_right(left_share: np.ndarray, bits: np.ndarray | Iterable[int]) -> BinaryImage:
    left = _binary(left_share, dimensions=1)
    values = _binary(bits, dimensions=1)
    if left.size != values.size * 2:
        raise ValueError("La share sinistra deve contenere due sotto-pixel per bit.")
    return np.bitwise_xor(left, np.repeat(values, 2))


def recover_deterministic(left_share: np.ndarray, right_share: np.ndarray) -> BinaryImage:
    left = _binary(left_share, dimensions=1)
    right = _binary(right_share, dimensions=1)
    if left.shape != right.shape or left.size % 2:
        raise ValueError("Share deterministiche non allineabili.")
    reconstructed = np.bitwise_or(left, right).reshape(-1, 2)
    return (reconstructed.sum(axis=1) == 2).astype(np.uint8)


def pointer_block(bit: int) -> BinaryImage:
    """Forma ricostruita 1x2: nero-bianco per 0, nero-nero per 1."""
    if bit not in (0, 1):
        raise ValueError("Il pointer deve valere 0 oppure 1.")
    return np.array([1, bit], dtype=np.uint8)


def pointer_blocks(pixels: np.ndarray | Iterable[int]) -> list[tuple[int, int]]:
    """Raggruppa una share di pointer in blocchi 1x2."""
    values = _binary(pixels, dimensions=1)
    if values.size % 2:
        raise ValueError("Una share di pointer deve contenere coppie di sotto-pixel.")
    return [(int(first), int(second)) for first, second in values.reshape(-1, 2)]


def read_pointer(block: np.ndarray | Iterable[int]) -> int:
    """Legge un blocco pointer ricostruito senza imporre l'orientamento dello zero."""
    checked = _binary(block, dimensions=1)
    if checked.size != 2:
        raise ValueError("Un pointer ricostruito deve contenere due sotto-pixel.")
    black_pixels = int(checked.sum())
    if black_pixels == 1:
        return 0
    if black_pixels == 2:
        return 1
    raise ValueError("Blocco pointer non valido: non può essere tutto trasparente.")
