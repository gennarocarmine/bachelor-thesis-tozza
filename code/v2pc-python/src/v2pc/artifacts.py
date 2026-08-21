"""Formato sicuro e portabile per salvare una costruzione V2PC."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .circuit import Circuit, parse_expression
from .protocol import (
    Construction,
    LeafMaterial,
    Transfer,
    TransferredLeafMaterial,
)

FORMAT_VERSION = 3


def _write(
    destination: str | Path,
    arrays_name: str,
    arrays: dict[str, np.ndarray],
    manifest: dict[str, Any],
) -> Path:
    folder = Path(destination)
    folder.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(folder / arrays_name, **arrays)
    (folder / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return folder


def _read(
    source: str | Path,
    arrays_name: str,
    expected_format: str,
) -> tuple[dict[str, Any], Circuit, list[dict[str, Any]], dict[str, np.ndarray]]:
    folder = Path(source)
    manifest_path = folder / "manifest.json"
    arrays_path = folder / arrays_name
    if not manifest_path.is_file() or not arrays_path.is_file():
        raise ValueError(f"La cartella non contiene manifest.json e {arrays_name}.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != expected_format:
        raise ValueError("Formato del pacchetto non riconosciuto.")
    if manifest.get("version") != FORMAT_VERSION:
        raise ValueError("Versione del pacchetto non supportata.")

    raw_leaves = manifest.get("leaves")
    if not isinstance(raw_leaves, list) or not all(
        isinstance(raw, dict) for raw in raw_leaves
    ):
        raise ValueError("Elenco delle share non valido.")

    with np.load(arrays_path, allow_pickle=False) as loaded:
        arrays = {name: loaded[name].astype(np.uint8) for name in loaded.files}
    return manifest, parse_expression(str(manifest["expression"])), raw_leaves, arrays


def _check_leaves(leaves: list, circuit: Circuit) -> None:
    if tuple(leaf.variable for leaf in leaves) != circuit.leaf_names:
        raise ValueError("Le share salvate non corrispondono alle foglie del circuito.")


def _leaf_entry(leaf, prefix: str, *extra: str) -> dict[str, Any]:
    entry = {
        "occurrence": leaf.occurrence,
        "variable": leaf.variable,
        "role": leaf.role,
        "party": leaf.party,
        "prefix": prefix,
    }
    entry.update({name: getattr(leaf, name) for name in extra})
    return entry


def save_construction(construction: Construction, destination: str | Path) -> Path:
    arrays: dict[str, np.ndarray] = {}
    leaves: list[dict[str, Any]] = []
    for leaf in construction.leaves:
        prefix = f"leaf_{leaf.occurrence:04d}"
        for value in (0, 1):
            arrays[f"{prefix}_image_{value}"] = leaf.images[value]
            arrays[f"{prefix}_pointer_{value}"] = leaf.pointer_values[value]
        leaves.append(_leaf_entry(leaf, prefix))

    return _write(
        destination,
        "shares.npz",
        arrays,
        {
            "format": "v2pc-construction",
            "version": FORMAT_VERSION,
            "expression": construction.circuit.expression,
            "side": construction.side,
            "seed": construction.seed,
            "gate_count": construction.circuit.gate_count,
            "depth": construction.circuit.depth,
            "leaves": leaves,
            "permutation_bits": list(construction.permutation_bits),
        },
    )


def load_construction(source: str | Path) -> Construction:
    manifest, circuit, raw_leaves, arrays = _read(
        source, "shares.npz", "v2pc-construction"
    )
    leaves = [
        LeafMaterial(
            occurrence=int(raw["occurrence"]),
            variable=str(raw["variable"]),
            role=str(raw["role"]),
            party=str(raw["party"]),
            images=(
                arrays[f"{raw['prefix']}_image_0"],
                arrays[f"{raw['prefix']}_image_1"],
            ),
            pointer_values=(
                arrays[f"{raw['prefix']}_pointer_0"],
                arrays[f"{raw['prefix']}_pointer_1"],
            ),
        )
        for raw in raw_leaves
    ]
    _check_leaves(leaves, circuit)
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

    arrays: dict[str, np.ndarray] = {}
    leaves: list[dict[str, Any]] = []
    for leaf in transfer.leaves:
        prefix = f"leaf_{leaf.occurrence:04d}"
        arrays[f"{prefix}_image"] = leaf.image
        arrays[f"{prefix}_pointer"] = leaf.pointer_value
        leaves.append(_leaf_entry(leaf, prefix, "delivery"))

    return _write(
        destination,
        "selected-shares.npz",
        arrays,
        {
            "format": "v2pc-transfer",
            "version": FORMAT_VERSION,
            "expression": transfer.circuit.expression,
            "side": transfer.side,
            "gate_count": transfer.circuit.gate_count,
            "depth": transfer.circuit.depth,
            "leaves": leaves,
        },
    )


def load_transfer(source: str | Path) -> Transfer:
    """Carica un pacchetto che non contiene le alternative scartate."""
    manifest, circuit, raw_leaves, arrays = _read(
        source, "selected-shares.npz", "v2pc-transfer"
    )
    leaves = [
        TransferredLeafMaterial(
            occurrence=int(raw["occurrence"]),
            variable=str(raw["variable"]),
            role=str(raw["role"]),
            party=str(raw["party"]),
            delivery=str(raw["delivery"]),
            image=arrays[f"{raw['prefix']}_image"],
            pointer_value=arrays[f"{raw['prefix']}_pointer"],
        )
        for raw in raw_leaves
    ]
    _check_leaves(leaves, circuit)
    return Transfer(
        circuit=circuit,
        side=int(manifest["side"]),
        seed=None,
        leaves=tuple(leaves),
    )
