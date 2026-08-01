"""Interfaccia a riga di comando."""

from __future__ import annotations

import argparse
from pathlib import Path

from .artifacts import (
    load_construction,
    load_transfer,
    save_construction,
    save_transfer,
)
from .circuit import Circuit, parse_expression
from .protocol import (
    DELIVERY_DIRECT,
    DELIVERY_SIMULATED_OT,
    build,
    evaluate,
    reconstruct,
    select_shares,
)

from .render import (
    export_leaf_alternatives,
    export_reconstruction,
    export_transferred_shares,
    pointer_parts,
    transferred_pointer_parts,
)


def parse_assignment(text: str) -> dict[str, int]:
    assignment: dict[str, int] = {}
    if not text.strip():
        return assignment
    for item in text.split(","):
        if "=" not in item:
            raise ValueError(f"Assegnamento non valido: {item!r}.")
        name, raw_value = (part.strip() for part in item.split("=", 1))
        if not name or raw_value not in {"0", "1"}:
            raise ValueError(f"Assegnamento non valido: {item!r}.")
        if name in assignment:
            raise ValueError(f"Variabile ripetuta: {name}.")
        assignment[name] = int(raw_value)
    return assignment


def _print_selected_shares(construction, assignment: dict[str, int]) -> None:
    print("Share selezionate (blocchi pointer 1x2 anteposti):")
    for leaf in construction.leaves:
        value = int(assignment[leaf.variable])
        clear, inner = pointer_parts(leaf, value)
        clear_text = "".join(map(str, clear)) or "-"
        inner_text = "".join(map(str, inner)) or "-"
        print(
            f"  S{leaf.occurrence + 1:02d} {leaf.variable}={value} "
            f"[{_delivery_label(leaf.party)}; "
            f"p={clear_text}; p_interni={inner_text}]"
        )


def _delivery_label(party_or_delivery: str) -> str:
    labels = {
        "alice": "Alice · consegna diretta",
        "bob": "Bob · OT simulato",
        "unassigned": "parte non assegnata · selezione locale",
        DELIVERY_DIRECT: "Alice · consegna diretta",
        DELIVERY_SIMULATED_OT: "Bob · OT simulato",
        "simulated_selection": "parte non assegnata · selezione locale",
    }
    return labels.get(party_or_delivery, party_or_delivery)


def _print_transferred_shares(transfer) -> None:
    print("Share ricevute (blocchi pointer 1x2 anteposti):")
    for leaf in transfer.leaves:
        clear, inner = transferred_pointer_parts(leaf)
        clear_text = "".join(map(str, clear)) or "-"
        inner_text = "".join(map(str, inner)) or "-"
        print(
            f"  S{leaf.occurrence + 1:02d} {leaf.variable} "
            f"[{_delivery_label(leaf.delivery)}; "
            f"p={clear_text}; p_interni={inner_text}]"
        )


def _print_simulation_notice() -> None:
    print(
        "Modalità: gli ingressi x di Alice sono consegnati direttamente; "
        "per gli ingressi y di Bob l'OT è simulato localmente. "
        "Un OT fisico o di rete non è implementato."
    )


def command_evaluate(args: argparse.Namespace) -> int:
    circuit = parse_expression(args.expression)
    assignment = parse_assignment(args.input)
    construction = build(circuit, side=args.side, seed=args.seed)
    result = evaluate(construction, assignment)
    status = "OK" if result.matches else "DISCORDANZA"
    print(f"Valore booleano: {result.expected}")
    print(f"Valore visuale:  {result.value} [{status}]")
    print(
        f"Circuito: {circuit.gate_count} porte, profondità {circuit.depth}, "
        f"{len(construction.leaves)} occorrenze di input"
    )
    _print_simulation_notice()
    _print_selected_shares(construction, assignment)
    return 0 if result.matches else 2


def command_construct(args: argparse.Namespace) -> int:
    circuit = parse_expression(args.expression)
    construction = build(circuit, side=args.side, seed=args.seed)
    destination = save_construction(construction, args.output)
    export_leaf_alternatives(construction, destination / "alternatives", scale=args.scale)
    print(f"Costruzione salvata in {destination.resolve()}")
    print(
        f"{len(construction.leaves)} fili di ingresso, "
        f"{construction.circuit.gate_count} porte, "
        f"{construction.total_pixels} pixel complessivi"
    )
    print("Ogni PNG contiene i blocchi pointer 1x2 anteposti alla share.")
    _print_simulation_notice()
    return 0


def command_transfer(args: argparse.Namespace) -> int:
    construction = load_construction(args.source)
    assignment = parse_assignment(args.input)
    transfer = select_shares(construction, assignment)
    destination = save_transfer(transfer, args.output)
    export_transferred_shares(transfer, destination / "shares", scale=args.scale)
    print(f"Share distribuite salvate in {destination.resolve()}")
    print(
        f"{len(transfer.leaves)} alternative conservate; "
        "le alternative non selezionate non sono presenti nel pacchetto."
    )
    direct_count = sum(leaf.delivery == DELIVERY_DIRECT for leaf in transfer.leaves)
    ot_count = sum(leaf.delivery == DELIVERY_SIMULATED_OT for leaf in transfer.leaves)
    other_count = len(transfer.leaves) - direct_count - ot_count
    print(
        f"Distribuzione: {direct_count} dirette da Alice, "
        f"{ot_count} mediante OT simulato per Bob"
        + (f", {other_count} selezioni locali non assegnate" if other_count else "")
        + "."
    )
    _print_simulation_notice()
    _print_transferred_shares(transfer)
    return 0


def _pointer_glyph(block) -> str:
    """Rende un blocco ricostruito: '.' sotto-pixel bianco, '#' sotto-pixel nero."""
    return "".join("#" if int(bit) else "." for bit in block)


def _print_steps(result) -> None:
    print("Passaggi della ricostruzione:")
    for step in result.steps:
        half = "sinistra" if step.selected_half == "left" else "destra"
        print(
            f"  G{step.index:<2} {step.operation:<3} "
            f"{step.left_source} + meta {half} di {step.right_source}"
            f"   pointer in chiaro={step.pointer}   lettura={step.decoded_value}"
        )
        recovered = step.recovered_pointer
        if step.recovered_pointer_value is not None:
            print(
                f"       pointer ricostruito [{_pointer_glyph(recovered[:2])}] = "
                f"{step.recovered_pointer_value}"
                f"   leggibile solo ora, lo usera G{step.index // 2}"
            )
            if recovered.size > 2:
                print(
                    f"       + {recovered.size - 2} sotto-pixel di share dei "
                    "pointer superiori, ancora illeggibili"
                )
        elif recovered.size == 0:
            print("       nessun pointer da ricostruire su questo filo")
        else:
            print(
                f"       {recovered.size} sotto-pixel di materiale pointer "
                f"trasportato: G{step.index // 2} ne ritagliera una meta"
            )


def command_reconstruct(args: argparse.Namespace) -> int:
    transfer = load_transfer(args.source)
    result = reconstruct(transfer)
    output = Path(args.output) if args.output else Path(args.source) / "reconstruction"
    export_reconstruction(transfer, result, output, scale=args.scale)
    print(f"Valore visuale ricostruito: {result.value}")
    _print_transferred_shares(transfer)
    _print_steps(result)
    print(f"Share ricevute, passaggi e uscita salvati in {output.resolve()}")
    return 0


def command_serve(args: argparse.Namespace) -> int:
    try:
        from .web import create_app
    except ImportError as exc:
        raise SystemExit("La demo web richiede Flask: installare il progetto con le dipendenze.") from exc
    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="v2pc",
        description=(
            "Simulatore didattico locale della costruzione Visual Two-Party "
            "Computation."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate_parser = subparsers.add_parser(
        "evaluate", help="costruisce e valuta una funzione in una sola esecuzione"
    )
    evaluate_parser.add_argument("expression")
    evaluate_parser.add_argument("--input", required=True, help="es. x1=0,y1=1")
    evaluate_parser.add_argument("--side", type=int, default=32)
    evaluate_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="seme opzionale per riprodurre una costruzione (predefinito: casuale)",
    )
    evaluate_parser.set_defaults(handler=command_evaluate)

    construct_parser = subparsers.add_parser(
        "construct", help="fase di Alice: genera tutte le alternative"
    )
    construct_parser.add_argument("expression")
    construct_parser.add_argument("--output", default="v2pc-construction")
    construct_parser.add_argument("--side", type=int, default=32)
    construct_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="seme opzionale per riprodurre una costruzione (predefinito: casuale)",
    )
    construct_parser.add_argument("--scale", type=int, default=8)
    construct_parser.set_defaults(handler=command_construct)

    transfer_parser = subparsers.add_parser(
        "transfer",
        help=(
            "consegna gli ingressi x di Alice e simula l'OT per gli ingressi y di Bob"
        ),
    )
    transfer_parser.add_argument("--source", required=True)
    transfer_parser.add_argument("--input", required=True, help="es. x1=0,y1=1")
    transfer_parser.add_argument("--output", default="v2pc-transfer")
    transfer_parser.add_argument("--scale", type=int, default=8)
    transfer_parser.set_defaults(handler=command_transfer)

    reconstruct_parser = subparsers.add_parser(
        "reconstruct",
        help="fase di Bob: ricostruisce usando soltanto le share ricevute",
    )
    reconstruct_parser.add_argument("--source", required=True)
    reconstruct_parser.add_argument("--output")
    reconstruct_parser.add_argument("--scale", type=int, default=8)
    reconstruct_parser.set_defaults(handler=command_reconstruct)

    serve_parser = subparsers.add_parser("serve", help="avvia la demo web locale")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=5000)
    serve_parser.add_argument("--debug", action="store_true")
    serve_parser.set_defaults(handler=command_serve)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
        return 2