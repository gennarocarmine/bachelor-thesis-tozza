"""Costruzione e valutazione delle due fasi del protocollo V2PC."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Iterator

import numpy as np

from .circuit import Circuit, Gate, Input, Node, Not, validate_assignment
from .gate import build_gate
from .visual import (
    BinaryImage,
    overlay,
    read_value,
    read_pointer,
    value_image,
)

PARTY_ALICE = "alice"
PARTY_BOB = "bob"
PARTY_UNASSIGNED = "unassigned"

DELIVERY_DIRECT = "direct"
DELIVERY_SIMULATED_OT = "simulated_ot"
DELIVERY_SIMULATED_SELECTION = "simulated_selection"


def input_party(variable: str) -> str:
    """Associa la convenzione x/Alice e y/Bob usata nel paper e nella demo."""
    prefix = variable[:1].lower()
    if prefix == "x":
        return PARTY_ALICE
    if prefix == "y":
        return PARTY_BOB
    return PARTY_UNASSIGNED


def delivery_for_party(party: str) -> str:
    """Restituisce il canale previsto per distribuire una share selezionata."""
    if party == PARTY_ALICE:
        return DELIVERY_DIRECT
    if party == PARTY_BOB:
        return DELIVERY_SIMULATED_OT
    return DELIVERY_SIMULATED_SELECTION


@dataclass(frozen=True)
class LeafMaterial:
    occurrence: int
    variable: str
    role: str
    party: str
    images: tuple[BinaryImage, BinaryImage]
    pointer_values: tuple[BinaryImage, BinaryImage]

    @property
    def pixel_count(self) -> int:
        return int(
            sum(image.size for image in self.images)
            + sum(pointer.size for pointer in self.pointer_values)
        )


@dataclass(frozen=True)
class Construction:
    circuit: Circuit
    side: int
    seed: int | None
    leaves: tuple[LeafMaterial, ...]
    permutation_bits: tuple[int, ...]

    @property
    def total_pixels(self) -> int:
        return sum(leaf.pixel_count for leaf in self.leaves)


@dataclass(frozen=True)
class TransferredLeafMaterial:
    """Un'alternativa distribuita direttamente o mediante OT simulato."""

    occurrence: int
    variable: str
    role: str
    party: str
    delivery: str
    image: BinaryImage
    pointer_value: BinaryImage

    @property
    def pixel_count(self) -> int:
        return int(self.image.size + self.pointer_value.size)


@dataclass(frozen=True)
class Transfer:
    """Pacchetto con le sole share selezionate, privo dei valori di input."""

    circuit: Circuit
    side: int
    seed: int | None
    leaves: tuple[TransferredLeafMaterial, ...]

    @property
    def total_pixels(self) -> int:
        return sum(leaf.pixel_count for leaf in self.leaves)


@dataclass(frozen=True)
class EvaluationStep:
    index: int
    operation: str
    left_source: str
    right_source: str
    output_name: str
    pointer: int
    selected_half: str
    decoded_value: int
    image: BinaryImage
    recovered_pointer: BinaryImage
    recovered_pointer_value: int | None


@dataclass(frozen=True)
class Evaluation:
    value: int
    expected: int | None
    output_image: BinaryImage
    steps: tuple[EvaluationStep, ...]

    @property
    def matches(self) -> bool | None:
        if self.expected is None:
            return None
        return self.value == self.expected


@dataclass
class _Wire:
    pointer_value: BinaryImage
    image: BinaryImage
    source: str


def build(
    circuit: Circuit,
    *,
    side: int = 32,
    seed: int | None = None,
    max_total_pixels: int = 50_000_000,
) -> Construction:
    """Fase di Alice: costruisce tutte le alternative senza conoscere gli input."""
    effective_seed = secrets.randbits(128) if seed is None else seed
    rng = np.random.default_rng(effective_seed)
    output_images = (value_image(0, side), value_image(1, side))
    empty = np.zeros(0, dtype=np.uint8)
    leaves: list[LeafMaterial] = []
    permutation_bits: list[int] = []
    occurrence = 0
    used_pixels = 0

    def descend(
        node: Node,
        images: tuple[BinaryImage, BinaryImage],
        pointer_values: tuple[BinaryImage, BinaryImage],
        role: str,
    ) -> None:
        nonlocal occurrence, used_pixels
        if isinstance(node, Input):
            material = LeafMaterial(
                occurrence=occurrence,
                variable=node.name,
                role=role,
                party=input_party(node.name),
                images=images,
                pointer_values=pointer_values,
            )
            occurrence += 1
            used_pixels += material.pixel_count
            if used_pixels > max_total_pixels:
                raise ValueError(
                    "La costruzione supera il limite di memoria configurato; "
                    "ridurre la formula o il lato delle immagini."
                )
            leaves.append(material)
            return

        if isinstance(node, Not):
            descend(
                node.child,
                (images[1], images[0]),
                (pointer_values[1], pointer_values[0]),
                role,
            )
            return

        gate = build_gate(node.operation, images, pointer_values, role, rng)
        permutation_bits.append(gate.permutation_bit)

        descend(
            node.left,
            gate.left_images,
            gate.left_pointers,
            "left",
        )
        descend(
            node.right,
            gate.right_images,
            gate.right_pointers,
            "right",
        )

    descend(circuit.root, output_images, (empty, empty), "output")
    return Construction(
        circuit=circuit,
        side=side,
        seed=effective_seed,
        leaves=tuple(leaves),
        permutation_bits=tuple(permutation_bits),
    )


def select_shares(
    construction: Construction,
    assignment: dict[str, int],
) -> Transfer:
    """Distribuisce x direttamente e simula l'OT per gli ingressi y di Bob."""
    validate_assignment(construction.circuit, assignment)
    leaves = tuple(
        TransferredLeafMaterial(
            occurrence=leaf.occurrence,
            variable=leaf.variable,
            role=leaf.role,
            party=leaf.party,
            delivery=delivery_for_party(leaf.party),
            image=leaf.images[int(assignment[leaf.variable])],
            pointer_value=leaf.pointer_values[int(assignment[leaf.variable])],
        )
        for leaf in construction.leaves
    )
    return Transfer(
        circuit=construction.circuit,
        side=construction.side,
        seed=None,
        leaves=leaves,
    )


def reconstruct(transfer: Transfer) -> Evaluation:
    """Ricostruisce usando soltanto le share ricevute, senza valori di input."""
    materials: Iterator[TransferredLeafMaterial] = iter(transfer.leaves)
    steps: list[EvaluationStep] = []
    def ascend(node: Node, gate_index: int = 1) -> _Wire:
        if isinstance(node, Input):
            try:
                material = next(materials)
            except StopIteration as exc:
                raise ValueError("Costruzione incompleta: manca una share di ingresso.") from exc
            if material.variable != node.name:
                raise ValueError("Le share trasferite non corrispondono al circuito.")
            return _Wire(
                pointer_value=material.pointer_value,
                image=material.image,
                source=f"S{material.occurrence + 1:02d}",
            )

        if isinstance(node, Not):
            return ascend(node.child, gate_index)

        left = ascend(node.left, gate_index * 2)
        right = ascend(node.right, gate_index * 2 + 1)
        if left.pointer_value.size < 2 or left.pointer_value.size % 2:
            raise ValueError("Pointer sinistro non valido.")
        pointer = read_pointer(left.pointer_value[:2])

        image_half_width = right.image.shape[1] // 2
        if image_half_width == 0 or right.image.shape[1] % 2:
            raise ValueError("La share destra non contiene due metà allineate.")
        selected_image = (
            right.image[:, :image_half_width]
            if pointer == 0
            else right.image[:, image_half_width:]
        )

        left_pointer_payload = left.pointer_value[2:]
        pointer_half_width = right.pointer_value.size // 2
        if right.pointer_value.size % 2:
            raise ValueError("Il canale destro del pointer non è divisibile in due metà.")
        selected_pointer = (
            right.pointer_value[:pointer_half_width]
            if pointer == 0
            else right.pointer_value[pointer_half_width:]
        )
        if left_pointer_payload.shape != selected_pointer.shape:
            raise ValueError("Le share dei pointer non sono allineabili.")
        recovered_pointer = np.bitwise_or(left_pointer_payload, selected_pointer)
        image = overlay(left.image, selected_image)

        # Il filo di uscita alimenta l'ingresso sinistro della porta soprastante
        # soltanto quando l'indice e' pari: solo in quel caso i primi due
        # sotto-pixel appena ricostruiti sono un pointer bit leggibile.
        feeds_left_input = gate_index % 2 == 0
        recovered_pointer_value = (
            read_pointer(recovered_pointer[:2])
            if feeds_left_input and recovered_pointer.size >= 2
            else None
        )

        output_name = f"G{gate_index}"
        steps.append(
            EvaluationStep(
                index=gate_index,
                operation=node.operation,
                left_source=left.source,
                right_source=right.source,
                output_name=output_name,
                pointer=pointer,
                selected_half="left" if pointer == 0 else "right",
                decoded_value=read_value(image),
                image=image,
                recovered_pointer=recovered_pointer,
                recovered_pointer_value=recovered_pointer_value,
            )
        )
        return _Wire(
            pointer_value=recovered_pointer,
            image=image,
            source=output_name,
        )

    output = ascend(transfer.circuit.root)
    try:
        next(materials)
    except StopIteration:
        pass
    else:
        raise ValueError("Costruzione non valida: sono presenti share in eccesso.")

    value = read_value(output.image)
    return Evaluation(
        value=value,
        expected=None,
        output_image=output.image,
        steps=tuple(steps),
    )


def evaluate(construction: Construction, assignment: dict[str, int]) -> Evaluation:
    """Scorciatoia locale: seleziona le share e ne esegue la ricostruzione."""
    transfer = select_shares(construction, assignment)
    reconstructed = reconstruct(transfer)
    return Evaluation(
        value=reconstructed.value,
        expected=construction.circuit.evaluate(assignment),
        output_image=reconstructed.output_image,
        steps=reconstructed.steps,
    )