"""
Interfaccia web (Flask) sopra l'implementazione del protocollo V2PC.

La demo non riscrive la logica: importa i moduli della tesi (circuit, protocol,
render, diagram) e li mette dietro un form. La prima pagina genera, per una
formula booleana e un input scelti dall'utente, le trasparenze stampabili di
ogni filo e l'immagine di uscita, con l'opzione di disegnare il circuito. La
seconda propone un esempio a due parti in cui gli input del computer restano
nascosti.

Avvio:  python app.py   poi apri  http://127.0.0.1:5000
"""
from __future__ import annotations
import io
import base64
import zipfile

import numpy as np
from flask import Flask, render_template, request, send_file
from PIL import Image

from cli import parse_expr
from circuit import input_leaves
from protocol import build
from render import eval_image, _wire_labels
from vc import read_value

app = Flask(__name__)

DISPLAY_SCALE = 3     # ingrandimento delle immagini a schermo
PRINT_SCALE = 8       # ingrandimento delle trasparenze nello ZIP da stampare


# --- immagini: da matrice 0/1 a PNG (1 = nero) ----------------------------
def _png_bytes(mat, scale: int) -> bytes:
    img = Image.fromarray(np.where(np.asarray(mat) == 1, 0, 255).astype(np.uint8), mode="L")
    img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _datauri(mat, scale: int) -> str:
    return "data:image/png;base64," + base64.b64encode(_png_bytes(mat, scale)).decode()


def _read_values(form, names) -> dict:
    """Legge i valori dei fili dal form (campo 'val_<nome>'), default 0."""
    return {n: 1 if form.get("val_" + n) == "1" else 0 for n in names}


def _random_seed() -> int:
    return int(np.random.default_rng().integers(0, 2**31 - 1))


def _bob_values(yvars, seed: int) -> dict:
    """Gli input del computer (variabili y), scelti a caso ma in modo riproducibile
    dal seme nascosto: cosi' restano fissi finche' non si cambia avversario."""
    rng = np.random.default_rng(seed)
    return {n: int(rng.integers(0, 2)) for n in yvars}


def _rebuild(form):
    """Ricostruisce circuito, valori e share da un form: prologo comune ai download."""
    c = parse_expr(form.get("formula", "").strip())
    values = _read_values(form, c.inputs)
    cc = build(c, int(form.get("size") or 32),
               np.random.default_rng(int(form.get("seed") or 0)))
    return c, values, cc


# --- costruzione delle share ----------------------------------------------
def _generate(formula: str, values: dict, size: int, seed: int,
              show_both: bool, show_circuit: bool, scale: int) -> dict:
    c = parse_expr(formula)
    values = {n: values.get(n, 0) for n in c.inputs}
    cc = build(c, size, np.random.default_rng(seed))

    leaves = input_leaves(c.root)
    wires = []
    for leaf, label in zip(leaves, _wire_labels(leaves)):
        v = values[leaf.name]
        w = {"label": label, "value": v,
             "used": _datauri(cc.input_shares[id(leaf)][v], scale)}
        if show_both:
            w["s0"] = _datauri(cc.input_shares[id(leaf)][0], scale)
            w["s1"] = _datauri(cc.input_shares[id(leaf)][1], scale)
        wires.append(w)

    out = eval_image(cc, values)
    result = {
        "wires": wires,
        "output": _datauri(out, scale),
        "letto": read_value(out),
        "vero": c.evaluate(values),
        "assign": values,
    }
    if show_circuit:
        from diagram import draw_circuit
        png = draw_circuit(cc, values)
        result["circuit"] = "data:image/png;base64," + base64.b64encode(png).decode()
    return result


def _generate_two(c, avals: dict, yvals: dict, size: int, seed: int,
                  reveal: bool, scale: int) -> dict:
    """Come la pagina 1, ma il valore dei fili del computer (y) resta nascosto
    finche' non si rivela: si mostrano le share, non i bit."""
    assignment = {n: {**avals, **yvals}.get(n, 0) for n in c.inputs}
    cc = build(c, size, np.random.default_rng(seed))

    leaves = input_leaves(c.root)
    wires = []
    for leaf, label in zip(leaves, _wire_labels(leaves)):
        bob = leaf.name.startswith("y")
        wires.append({
            "label": label,
            "owner": "bob" if bob else "alice",
            "value": (assignment[leaf.name] if (not bob or reveal) else None),
            "used": _datauri(cc.input_shares[id(leaf)][assignment[leaf.name]], scale),
        })

    out = eval_image(cc, assignment)
    return {"wires": wires, "output": _datauri(out, scale), "letto": read_value(out)}


# --- route ----------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", result=None,
                           formula="(x1 | y1) & ~(x2 & y2)", size=32, seed="")


@app.route("/genera", methods=["POST"])
def genera():
    formula = request.form.get("formula", "").strip()
    size = int(request.form.get("size") or 32)
    seed_raw = request.form.get("seed", "").strip()
    seed = int(seed_raw) if seed_raw else _random_seed()
    show_both = request.form.get("show_both") == "on"
    show_circuit = request.form.get("show_circuit") == "on"

    try:
        c = parse_expr(formula)
    except Exception as e:
        return render_template("index.html", result=None, error=str(e),
                               formula=formula, size=size, seed="",
                               show_both=show_both, show_circuit=show_circuit)

    values = _read_values(request.form, c.inputs)
    result = _generate(formula, values, size, seed, show_both, show_circuit,
                       DISPLAY_SCALE)
    return render_template("index.html", result=result, formula=formula,
                           size=size, seed=seed, show_both=show_both,
                           show_circuit=show_circuit)


@app.route("/scarica", methods=["POST"])
def scarica():
    c, values, cc = _rebuild(request.form)
    leaves = input_leaves(c.root)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for leaf, label in zip(leaves, _wire_labels(leaves)):
            z.writestr(f"{label}.png",
                       _png_bytes(cc.input_shares[id(leaf)][values[leaf.name]], PRINT_SCALE))
        z.writestr("uscita.png", _png_bytes(eval_image(cc, values), PRINT_SCALE))
    buf.seek(0)
    return send_file(buf, mimetype="application/zip", as_attachment=True,
                     download_name="share_v2pc.zip")


@app.route("/scarica-circuito", methods=["POST"])
def scarica_circuito():
    _, values, cc = _rebuild(request.form)
    from diagram import draw_circuit
    return send_file(io.BytesIO(draw_circuit(cc, values)), mimetype="image/png",
                     as_attachment=True, download_name="circuito_v2pc.png")


@app.route("/due", methods=["GET", "POST"])
def due():
    if request.method == "GET":
        return render_template("due.html", result=None,
                               formula="(x1 | y1) & ~(x2 & y2)", size=32, s="")

    formula = request.form.get("formula", "").strip()
    size = int(request.form.get("size") or 32)
    action = request.form.get("action", "calcola")

    try:
        c = parse_expr(formula)
    except Exception as e:
        return render_template("due.html", result=None, error=str(e),
                               formula=formula, size=size, s="")

    s_raw = request.form.get("s", "").strip()
    s = _random_seed() if (action == "nuovo" or not s_raw) else int(s_raw)
    reveal = action == "rivela"

    yvars = [n for n in c.inputs if n.startswith("y")]
    avars = [n for n in c.inputs if not n.startswith("y")]
    avals = _read_values(request.form, avars)
    yvals = _bob_values(yvars, s)

    result = _generate_two(c, avals, yvals, size, s, reveal, DISPLAY_SCALE)
    result.update({"avars": avars, "yvars": yvars, "avals": avals, "reveal": reveal})
    if reveal:
        result["yvals"] = yvals
    return render_template("due.html", result=result, formula=formula, size=size, s=s)


if __name__ == "__main__":
    app.run(debug=True, port=5000)