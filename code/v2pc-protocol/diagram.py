"""
Disegno del circuito con le share sui fili.

Dopo la costruzione e dato un input, ogni filo porta una
immagine (la share che vi transita) e ogni porta ha il suo pointer bit. Questo
modulo disegna l'albero del circuito dal basso verso l'alto: gli ingressi in
fondo, l'uscita in cima. Su ogni filo appoggia la miniatura della share; sul
filo sinistro di ogni porta scrive il pointer bit p; in cima mostra l'immagine
di uscita ricostruita. Il disegno serve sia nella demo web sia come figura.
"""
from __future__ import annotations
import io

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

from circuit import Input, Gate, Not, gate_value, input_leaves
from vgess import eval_gate
from vc import read_value


def _annotate(cc, assignment: dict) -> dict:
    """Per ogni nodo: l'immagine sul suo filo di uscita, il valore vero e, per le
    porte, il pointer bit p."""
    info: dict = {}

    def rec(node):
        if isinstance(node, Input):
            v = assignment[node.name]
            img = cc.input_shares[id(node)][v]
            info[id(node)] = {"img": img, "val": v}
            return img, v
        if isinstance(node, Not):
            cimg, cv = rec(node.child)
            info[id(node)] = {"img": cimg, "val": 1 - cv}
            return cimg, 1 - cv
        lim, lv = rec(node.left)
        rim, rv = rec(node.right)
        p = lv ^ cc.bmap[id(node)]
        out = eval_gate((p, lim), rim)
        info[id(node)] = {"img": out, "val": gate_value(node.op, lv, rv), "p": p}
        return out, info[id(node)]["val"]

    rec(cc.circuit.root)
    return info


def _rgb(mat, k: int = 6) -> np.ndarray:
    """Da matrice 0/1 a immagine RGB ingrandita (1 = nero), senza sfocature."""
    a = np.asarray(mat)
    g = np.where(a == 1, 0.0, 1.0)
    g = np.kron(g, np.ones((k, k)))
    return np.stack([g, g, g], axis=-1)


def _oimage(mat, size: int, target_px: float = 26.0, max_w: float = 92.0) -> OffsetImage:
    """Miniatura a altezza fissa, ma con larghezza massima: le share molto larghe
    (fili destri profondi) vengono rimpicciolite invece di invadere le colonne
    vicine."""
    k = 6
    w = np.asarray(mat).shape[1]
    zoom = min(target_px / (size * k), max_w / (w * k))
    return OffsetImage(_rgb(mat, k), zoom=zoom)


def draw_circuit(cc, assignment: dict, path: str | None = None):
    """Disegna il circuito con le share. Se ``path`` e' dato salva un PNG,
    altrimenti restituisce i byte PNG (per la demo web)."""
    root = cc.circuit.root
    size = cc.size
    info = _annotate(cc, assignment)

    leaves = input_leaves(root)
    slot = {id(l): i for i, l in enumerate(leaves)}

    hmemo: dict = {}
    def height(n):
        k = id(n)
        if k in hmemo:
            return hmemo[k]
        if isinstance(n, Input):
            h = 0
        elif isinstance(n, Not):
            h = 1 + height(n.child)
        else:
            h = 1 + max(height(n.left), height(n.right))
        hmemo[k] = h
        return h

    SX = 2.4      # spaziatura orizzontale tra i fili, per lasciar posto alle share
    pos: dict = {}
    def place(n):
        if isinstance(n, Input):
            x = slot[id(n)] * SX
        elif isinstance(n, Not):
            place(n.child)
            x = pos[id(n.child)][0]
        else:
            place(n.left)
            place(n.right)
            x = (pos[id(n.left)][0] + pos[id(n.right)][0]) / 2.0
        pos[id(n)] = (x, float(height(n)))
    place(root)

    L = len(leaves)
    H = height(root)
    maxx = (L - 1) * SX
    fig_w = max(7.0, (maxx + 1.8) * 1.25)
    fig_h = max(4.5, (H + 1.4) * 1.9)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(-0.95, maxx + 0.95)
    ax.set_ylim(-0.7, H + 1.3)
    ax.axis("off")

    edge_col = "#9a9a9a"

    def node_box(n):
        x, y = pos[id(n)]
        if isinstance(n, Input):
            iv = info[id(n)]
            ax.text(x, y, f"{n.name}={iv['val']}", ha="center", va="center", fontsize=10, family="monospace", bbox=dict(boxstyle="round,pad=0.3", fc="#f2f2ef", ec="#c9c9c4"))
        elif isinstance(n, Not):
            ax.text(x, y, "¬", ha="center", va="center", fontsize=12, bbox=dict(boxstyle="circle,pad=0.25", fc="#ffffff", ec="#c9c9c4"))
        else:
            ax.text(x, y, n.op, ha="center", va="center", fontsize=10, weight="bold", bbox=dict(boxstyle="round,pad=0.35", fc="#eaf1fb", ec="#185fa5"))

    def edge(child, parent, left=False):
        cx, cy = pos[id(child)]
        px, py = pos[id(parent)]
        ax.plot([cx, px], [cy, py], color=edge_col, lw=1.1, zorder=1)
        mx, my = (cx + px) / 2.0, (cy + py) / 2.0
        ab = AnnotationBbox(_oimage(info[id(child)]["img"], size), (mx, my), frameon=True, pad=0.15, bboxprops=dict(edgecolor="#c9c9c4", lw=0.6))
        ax.add_artist(ab)
        if left and "p" in info[id(parent)]:
            t = 0.76
            lx, ly = cx + t * (px - cx), cy + t * (py - cy)
            ax.text(lx - 0.05, ly, f"p={info[id(parent)]['p']}", ha="right",
                    va="center", fontsize=9, color="#185fa5", family="monospace",
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9))

    def walk(n):
        if isinstance(n, Not):
            edge(n.child, n)
            walk(n.child)
        elif isinstance(n, Gate):
            edge(n.left, n, left=True)
            edge(n.right, n)
            walk(n.left)
            walk(n.right)
        node_box(n)

    walk(root)

    rx, ry = pos[id(root)]
    ax.plot([rx, rx], [ry, ry + 1.0], color=edge_col, lw=1.1, zorder=1)
    ab = AnnotationBbox(_oimage(info[id(root)]["img"], size, target_px=42), (rx, ry + 1.0), frameon=True, pad=0.15, bboxprops=dict(edgecolor="#185fa5", lw=0.8))
    ax.add_artist(ab)
    ax.text(rx + 0.28, ry + 1.0, f"uscita = {read_value(info[id(root)]['img'])}",
            ha="left", va="center", fontsize=10, family="monospace")

    fig.tight_layout()
    if path:
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()
