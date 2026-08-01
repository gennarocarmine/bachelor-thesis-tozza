"""Costruzione visuale di una porta tramite GenGESS."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .circuit import apply_gate
from .visual import (
    BinaryImage,
    deterministic_left,
    deterministic_right,
    multi_secret_share,
    pointer_block,
    read_pointer,
)


@dataclass(frozen=True)
class GateShares:
    left_images: tuple[BinaryImage, BinaryImage]
    right_images: tuple[BinaryImage, BinaryImage]
    left_pointers: tuple[BinaryImage, BinaryImage]
    right_pointers: tuple[BinaryImage, BinaryImage]
    permutation_bit: int


def _concatenate(
    first: dict[int, BinaryImage],
    second: dict[int, BinaryImage],
    permutation_bit: int,
) -> tuple[BinaryImage, BinaryImage]:
    left, right = (first, second) if permutation_bit == 0 else (second, first)
    return tuple(
        np.concatenate((left[value], right[value]), axis=-1) for value in (0, 1)
    )  # type: ignore[return-value]


def build_gate(
    operation: str,
    output_images: tuple[BinaryImage, BinaryImage],
    output_pointers: tuple[BinaryImage, BinaryImage],
    output_role: str,
    rng: np.random.Generator,
) -> GateShares:
    """Produce le alternative dei due fili di ingresso di una porta."""

    def output_image(left_value: int, right_value: int) -> BinaryImage:
        return output_images[apply_gate(operation, left_value, right_value)]

    def output_pointer(left_value: int, right_value: int) -> BinaryImage:
        return output_pointers[apply_gate(operation, left_value, right_value)]

    a_common, a_second, a_third = multi_secret_share(
        output_image(0, 0), output_image(0, 1), rng
    )
    b_common, b_second, b_third = multi_secret_share(
        output_image(1, 0), output_image(1, 1), rng
    )

    permutation = int(rng.integers(0, 2))

    right_images = _concatenate(
        {0: a_second, 1: a_third},
        {0: b_second, 1: b_third},
        permutation,
    )

    if output_role not in {"output", "left", "right"}:
        raise ValueError(f"Ruolo del filo non valido: {output_role}.")

    if output_pointers[0].shape != output_pointers[1].shape:
        raise ValueError("Le alternative del pointer devono avere la stessa lunghezza.")

    if output_role in {"output", "left"}:
        if output_pointers[0].size:
            if output_pointers[0].size < 2 or output_pointers[0].size % 2:
                raise ValueError("Il pointer deve essere formato da blocchi 1x2.")
            if not np.array_equal(output_pointers[0][2:], output_pointers[1][2:]):
                raise ValueError(
                    "Le share dei pointer già generate devono essere propagate "
                    "senza dipendere dal valore del filo."
                )
            output_bits = (
                read_pointer(output_pointers[0][:2]),
                read_pointer(output_pointers[1][:2]),
            )
            carried = output_pointers[0][2:]
            pointer_left = deterministic_left(1, rng)

            def right_pointer(left_value: int, right_value: int) -> BinaryImage:
                bit = output_bits[apply_gate(operation, left_value, right_value)]
                return np.concatenate(
                    (
                        deterministic_right(
                            pointer_left,
                            np.array([bit], dtype=np.uint8),
                        ),
                        carried,
                    )
                )

            left_payloads = (
                np.concatenate((pointer_left, carried)),
                np.concatenate((pointer_left, carried)),
            )
        else:
            empty = np.zeros(0, dtype=np.uint8)
            left_payloads = (empty, empty)

            def right_pointer(left_value: int, right_value: int) -> BinaryImage:
                return empty
    else:
        # Il valore da propagare è già una share deterministica di un pointer
        # appartenente a una porta superiore. Non viene condiviso di nuovo:
        # la share destra viene copiata nella metà selezionabile, mentre una
        # striscia trasparente sul filo sinistro la lascia invariata all'OR.
        empty_payload = np.zeros(output_pointers[0].size, dtype=np.uint8)
        left_payloads = (empty_payload, empty_payload)

        def right_pointer(left_value: int, right_value: int) -> BinaryImage:
            return output_pointer(left_value, right_value)

    left_pointers = (
        np.concatenate((pointer_block(permutation), left_payloads[0])),
        np.concatenate((pointer_block(1 - permutation), left_payloads[1])),
    )
    right_pointers = _concatenate(
        {value: right_pointer(0, value) for value in (0, 1)},
        {value: right_pointer(1, value) for value in (0, 1)},
        permutation,
    )

    return GateShares(
        left_images=(a_common, b_common),
        right_images=right_images,
        left_pointers=left_pointers,
        right_pointers=right_pointers,
        permutation_bit=permutation,
    )
