"""Formato sicuro e portabile per salvare una costruzione V2PC."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .circuit import parse_expression
from .protocol import (
    Construction,
    LeafMaterial,
    Transfer,
    TransferredLeafMaterial,
    delivery_for_party,
    input_party,
)

FORMAT_VERSION = 3
SUPPORTED_FORMAT_VERSIONS = {2, FORMAT_VERSION}


def save_construction(construction: Construction, destination: str | Path) -> Path:
    folder = Path(destination)
    folder.mkdir(parents=True, exist_ok=True)

    arrays: dict[str, np.ndarray] = {}
    leaves: list[dict[str, object]] = []
    for leaf in construction.leaves:
        prefix = f"leaf_{leaf.occurrence:04d}"
        arrays[f"{prefix}_image_0"] = leaf.images[0]
        arrays[f"{prefix}_image_1"] = leaf.images[1]
        arrays[f"{prefix}_pointer_0"] = leaf.pointer_values[0]
        arrays[f"{prefix}_pointer_1"] = leaf.pointer_values[1]
        leaves.append(
            {
                "occurrence": leaf.occurrence,
                "variable": leaf.variable,
                "role": leaf.role,
                "party": leaf.party,
                "prefix": prefix,
            }
        )

    np.savez_compressed(folder / "shares.npz", **arrays)
    manifest = {
        "format": "v2pc-construction",
        "version": FORMAT_VERSION,
        "expression": construction.circuit.expression,
        "side": construction.side,
        "seed": construction.seed,
        "gate_count": construction.circuit.gate_count,
        "depth": construction.circuit.depth,
        "leaves": leaves,
        "permutation_bits": list(construction.permutation_bits),
    }
    (folder / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return folder


def load_construction(source: str | Path) -> Construction:
    folder = Path(source)
    manifest_path = folder / "manifest.json"
    arrays_path = folder / "shares.npz"
    if not manifest_path.is_file() or not arrays_path.is_file():
        raise ValueError("La cartella non contiene manifest.json e shares.npz.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "v2pc-construction":
        raise ValueError("Formato della costruzione non riconosciuto.")
    if manifest.get("version") not in SUPPORTED_FORMAT_VERSIONS:
        raise ValueError("Versione della costruzione non supportata.")

    circuit = parse_expression(str(manifest["expression"]))
    raw_leaves = manifest.get("leaves")
    if not isinstance(raw_leaves, list):
        raise ValueError("Elenco delle share non valido.")

    leaves: list[LeafMaterial] = []
    with np.load(arrays_path, allow_pickle=False) as arrays:
        for raw in raw_leaves:
            if not isinstance(raw, dict):
                raise ValueError("Voce di share non valida.")
            prefix = str(raw["prefix"])
            leaves.append(
                LeafMaterial(
                    occurrence=int(raw["occurrence"]),
                    variable=str(raw["variable"]),
                    role=str(raw["role"]),
                    party=str(
                        raw.get("party", input_party(str(raw["variable"])))
                    ),
                    images=(
                        arrays[f"{prefix}_image_0"].astype(np.uint8),
                        arrays[f"{prefix}_image_1"].astype(np.uint8),
                    ),
                    pointer_values=(
                        arrays[f"{prefix}_pointer_0"].astype(np.uint8),
                        arrays[f"{prefix}_pointer_1"].astype(np.uint8),
                    ),
                )
            )

    if tuple(leaf.variable for leaf in leaves) != circuit.leaf_names:
        raise ValueError("Le share salvate non corrispondono alle foglie del circuito.")

    return Construction(
        circuit=circuit,
        side=int(manifest["side"]),
        seed=manifest.get("seed"),
        leaves=tuple(leaves),
        permutation_bits=tuple(int(bit) for bit in manifest.get("permutation_bits", [])),
    )


def save_transfer(transfer: Transfer, destination: str | Path) -> Path:
    """Salva soltanto le share distribuite, senza assegnamento né alternative."""
    folder = Path(destination)
    if folder.exists() and any(folder.iterdir()):
        raise ValueError(
            "La destinazione del trasferimento deve essere nuova o vuota, "
            "per evitare di conservare alternative precedenti."
        )
    folder.mkdir(parents=True, exist_ok=True)

    arrays: dict[str, np.ndarray] = {}
    leaves: list[dict[str, object]] = []
    for leaf in transfer.leaves:
        prefix = f"leaf_{leaf.occurrence:04d}"
        arrays[f"{prefix}_image"] = leaf.image
        arrays[f"{prefix}_pointer"] = leaf.pointer_value
        leaves.append(
            {
                "occurrence": leaf.occurrence,
                "variable": leaf.variable,
                "role": leaf.role,
                "party": leaf.party,
                "delivery": leaf.delivery,
                "prefix": prefix,
            }
        )

    np.savez_compressed(folder / "selected-shares.npz", **arrays)
    manifest = {
        "format": "v2pc-transfer",
        "version": FORMAT_VERSION,
        "expression": transfer.circuit.expression,
        "side": transfer.side,
        "gate_count": transfer.circuit.gate_count,
        "depth": transfer.circuit.depth,
        "leaves": leaves,
    }
    (folder / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return folder


def load_transfer(source: str | Path) -> Transfer:
    """Carica un pacchetto che non contiene le alternative scartate."""
    folder = Path(source)
    manifest_path = folder / "manifest.json"
    arrays_path = folder / "selected-shares.npz"
    if not manifest_path.is_file() or not arrays_path.is_file():
        raise ValueError(
            "La cartella non contiene manifest.json e selected-shares.npz."
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "v2pc-transfer":
        raise ValueError("Il pacchetto non contiene share trasferite.")
    if manifest.get("version") not in SUPPORTED_FORMAT_VERSIONS:
        raise ValueError("Versione del trasferimento non supportata.")

    circuit = parse_expression(str(manifest["expression"]))
    raw_leaves = manifest.get("leaves")
    if not isinstance(raw_leaves, list):
        raise ValueError("Elenco delle share trasferite non valido.")

    leaves: list[TransferredLeafMaterial] = []
    with np.load(arrays_path, allow_pickle=False) as arrays:
        for raw in raw_leaves:
            if not isinstance(raw, dict):
                raise ValueError("Voce di share trasferita non valida.")
            prefix = str(raw["prefix"])
            party = str(raw.get("party", input_party(str(raw["variable"]))))
            leaves.append(
                TransferredLeafMaterial(
                    occurrence=int(raw["occurrence"]),
                    variable=str(raw["variable"]),
                    role=str(raw["role"]),
                    party=party,
                    delivery=str(
                        raw.get("delivery", delivery_for_party(party))
                    ),
                    image=arrays[f"{prefix}_image"].astype(np.uint8),
                    pointer_value=arrays[f"{prefix}_pointer"].astype(np.uint8),
                )
            )

    if tuple(leaf.variable for leaf in leaves) != circuit.leaf_names:
        raise ValueError("Le share trasferite non corrispondono alle foglie del circuito.")

    return Transfer(
        circuit=circuit,
        side=int(manifest["side"]),
        seed=None,
        leaves=tuple(leaves),
    )
