"""Demo web locale costruita sullo stesso nucleo usato dalla CLI."""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Any

from flask import Flask, render_template, request, send_file

from .circuit import Gate, Input, Node, Not, parse_expression
from .cli import parse_assignment
from .printkit import build_construction_kit, build_print_kit
from .protocol import (
    DELIVERY_DIRECT,
    DELIVERY_SIMULATED_OT,
    Evaluation,
    build,
    reconstruct,
    select_shares,
)
from .render import (
    image_png_bytes,
    printable_transferred_share_to_pil,
    transferred_pointer_parts,
)

DEFAULT_EXPRESSION = "(x1|y1) & ((x2&y2) & (x3|y3))"
DEFAULT_ASSIGNMENT = "x1=0,y1=1,x2=1,y2=1,x3=1,y3=0"


def _data_url(data: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


def _pil_data_url(image) -> str:
    stream = BytesIO()
    image.save(stream, format="PNG")
    return _data_url(stream.getvalue())


def _pointer_blocks(bits: tuple[int, ...]) -> list[tuple[int, int]]:
    if len(bits) % 2:
        raise ValueError("Una share di pointer deve contenere coppie di sotto-pixel.")
    return [tuple(bits[index : index + 2]) for index in range(0, len(bits), 2)]


def _form_variables(expression: str, assignment_text: str) -> list[dict[str, Any]]:
    try:
        names = parse_expression(expression).variables
    except ValueError:
        names = ()
    try:
        values = parse_assignment(assignment_text)
    except ValueError:
        values = {}
    return [{"name": name, "value": values.get(name, 0)} for name in names]


def _circuit_diagram(
    root: Node,
    shares: list[dict[str, Any]],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    share_iterator = iter(shares)
    step_iterator = iter(steps)

    def visit(node: Node) -> dict[str, Any]:
        if isinstance(node, Input):
            share = next(share_iterator)
            return {
                "kind": "input",
                "label": node.name,
                "share": share,
                "children": [],
            }
        if isinstance(node, Not):
            return {
                "kind": "not",
                "label": "NOT",
                "children": [visit(node.child)],
            }
        if isinstance(node, Gate):
            left = visit(node.left)
            right = visit(node.right)
            step = next(step_iterator)
            return {
                "kind": "gate",
                "label": node.operation,
                "step": step,
                "children": [left, right],
            }
        raise TypeError("Nodo del circuito non riconosciuto.")

    return visit(root)


def _build_construction(payload: dict[str, Any]):
    expression = str(payload.get("expression", DEFAULT_EXPRESSION)).strip()
    side = int(payload.get("side", 32))
    raw_seed = payload.get("seed")
    seed = None if raw_seed is None or str(raw_seed).strip() == "" else int(raw_seed)
    if seed is None:
        stored_seed = str(payload.get("construction_seed", "")).strip()
        stored_expression = str(payload.get("construction_expression", "")).strip()
        stored_side = str(payload.get("construction_side", "")).strip()
        if (
            stored_seed
            and stored_expression == expression
            and stored_side == str(side)
        ):
            seed = int(stored_seed)
    if side > 64:
        raise ValueError("Nella demo web il lato massimo è 64.")

    circuit = parse_expression(expression)
    if circuit.gate_count > 12:
        raise ValueError("Nella demo web sono ammesse al massimo 12 porte.")
    construction = build(
        circuit,
        side=side,
        seed=seed,
        max_total_pixels=12_000_000,
    )
    return expression, side, construction.seed, circuit, construction


def _evaluate_payload(payload: dict[str, Any]):
    expression, side, seed, circuit, construction = _build_construction(payload)
    raw_assignment = payload.get("assignment", DEFAULT_ASSIGNMENT)
    if isinstance(raw_assignment, dict):
        assignment = {str(name): int(value) for name, value in raw_assignment.items()}
        assignment_text = ",".join(f"{name}={value}" for name, value in assignment.items())
    else:
        assignment_text = str(raw_assignment).strip()
        assignment = parse_assignment(assignment_text)
    transfer = select_shares(construction, assignment)
    reconstructed = reconstruct(transfer)
    result = Evaluation(
        value=reconstructed.value,
        expected=circuit.evaluate(assignment),
        output_image=reconstructed.output_image,
        steps=reconstructed.steps,
    )
    return (
        expression,
        assignment,
        assignment_text,
        side,
        seed,
        circuit,
        construction,
        transfer,
        result,
    )


def _run(payload: dict[str, Any]) -> dict[str, Any]:
    (
        expression,
        assignment,
        assignment_text,
        side,
        seed,
        circuit,
        construction,
        transfer,
        result,
    ) = _evaluate_payload(payload)

    selected = []
    for leaf in transfer.leaves:
        value = assignment[leaf.variable]
        pointer_clear, pointer_inner = transferred_pointer_parts(leaf)
        selected.append(
            {
                "occurrence": leaf.occurrence + 1,
                "variable": leaf.variable,
                "value": value,
                "role": leaf.role,
                "role_label": {
                    "left": "filo sinistro",
                    "right": "filo destro",
                    "output": "filo di uscita",
                }[leaf.role],
                "party": leaf.party,
                "party_label": {
                    "alice": "Alice",
                    "bob": "Bob",
                    "unassigned": "parte non assegnata",
                }[leaf.party],
                "delivery": leaf.delivery,
                "delivery_label": {
                    "direct": "consegna diretta",
                    "simulated_ot": "OT simulato",
                    "simulated_selection": "selezione locale",
                }[leaf.delivery],
                "pointer_clear": pointer_clear,
                "pointer_inner": pointer_inner,
                "pointer_clear_blocks": [(1, bit) for bit in pointer_clear],
                "pointer_inner_blocks": _pointer_blocks(pointer_inner),
                "image": _data_url(image_png_bytes(leaf.image, scale=4)),
                "paper_image": _pil_data_url(
                    printable_transferred_share_to_pil(leaf, scale=4)
                ),
            }
        )

    steps = [
        {
            "index": step.index,
            "operation": step.operation,
            "left_source": step.left_source,
            "right_source": step.right_source,
            "output_name": step.output_name,
            "pointer": step.pointer,
            "selected_half": step.selected_half,
            "selected_half_label": (
                "sinistra" if step.selected_half == "left" else "destra"
            ),
            "decoded_value": step.decoded_value,
            "image": _data_url(image_png_bytes(step.image, scale=4)),
        }
        for step in result.steps
    ]
    direct_count = sum(
        leaf.delivery == DELIVERY_DIRECT for leaf in transfer.leaves
    )
    ot_count = sum(
        leaf.delivery == DELIVERY_SIMULATED_OT for leaf in transfer.leaves
    )
    response = {
        "expression": expression,
        "assignment": assignment,
        "assignment_text": assignment_text,
        "side": side,
        "seed": seed,
        "variables": list(circuit.variables),
        "gate_count": circuit.gate_count,
        "depth": circuit.depth,
        "alternative_count": 2 * len(construction.leaves),
        "transferred_count": len(transfer.leaves),
        "alice_direct_count": direct_count,
        "bob_ot_count": ot_count,
        "unassigned_count": len(transfer.leaves) - direct_count - ot_count,
        "expected": result.expected,
        "visual": result.value,
        "matches": result.matches,
        "output": _data_url(image_png_bytes(result.output_image, scale=5)),
        "shares": selected,
        "steps": steps,
    }
    response["circuit"] = _circuit_diagram(circuit.root, selected, steps)
    return response


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=64 * 1024)

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            expression=DEFAULT_EXPRESSION,
            assignment=DEFAULT_ASSIGNMENT,
            input_variables=_form_variables(
                DEFAULT_EXPRESSION, DEFAULT_ASSIGNMENT
            ),
            side=32,
            seed=None,
            construction_seed=None,
            construction_expression="",
            construction_side="",
            result=None,
            error=None,
        )

    @app.post("/")
    def evaluate_page():
        form = request.form.to_dict()
        try:
            result = _run(form)
            context = {
                **result,
                "assignment": result["assignment_text"],
                "seed": form.get("seed", ""),
                "construction_seed": result["seed"],
                "construction_expression": result["expression"],
                "construction_side": result["side"],
                "input_variables": [
                    {"name": name, "value": result["assignment"][name]}
                    for name in result["variables"]
                ],
                "result": result,
                "error": None,
            }
            return render_template("index.html", **context)
        except (ValueError, MemoryError) as exc:
            return (
                render_template(
                    "index.html",
                    expression=form.get("expression", DEFAULT_EXPRESSION),
                    assignment=form.get("assignment", DEFAULT_ASSIGNMENT),
                    input_variables=_form_variables(
                        form.get("expression", DEFAULT_EXPRESSION),
                        form.get("assignment", DEFAULT_ASSIGNMENT),
                    ),
                    side=form.get("side", 32),
                    seed=form.get("seed", ""),
                    construction_seed=form.get("construction_seed", ""),
                    construction_expression=form.get("construction_expression", ""),
                    construction_side=form.get("construction_side", ""),
                    result=None,
                    error=str(exc),
                ),
                400,
            )

    @app.post("/download-shares")
    def download_shares():
        try:
            (
                _expression,
                assignment,
                _assignment_text,
                _side,
                _seed,
                _circuit,
                construction,
                transfer,
                evaluation,
            ) = _evaluate_payload(request.form.to_dict())
            archive = build_print_kit(transfer, evaluation)
            return send_file(
                archive,
                mimetype="application/zip",
                as_attachment=True,
                download_name="v2pc-kit-stampa-share.zip",
            )
        except (ValueError, MemoryError) as exc:
            return f"Impossibile creare il kit di stampa: {exc}\n", 400

    @app.post("/download-all-shares")
    def download_all_shares():
        try:
            (
                _expression,
                _side,
                _seed,
                _circuit,
                construction,
            ) = _build_construction(request.form.to_dict())
            archive = build_construction_kit(construction)
            response = send_file(
                archive,
                mimetype="application/zip",
                as_attachment=True,
                download_name="v2pc-tutte-le-alternative.zip",
            )
            response.headers["X-V2PC-Seed"] = str(construction.seed)
            return response
        except (ValueError, MemoryError) as exc:
            return f"Impossibile creare tutte le share: {exc}\n", 400

    @app.get("/health")
    def health():
        return "ok\n", 200, {"Content-Type": "text/plain; charset=utf-8"}

    return app
