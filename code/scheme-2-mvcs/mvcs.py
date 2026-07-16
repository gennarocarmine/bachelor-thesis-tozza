"""
Scheme-2-MVCS: condivisione di due immagini segrete su tre share.
La funzione Shr segue esattamente lo pseudocodice della tesi (Algoritmo alg:mvcs):
una stessa sh1 ricostruisce due segreti diversi,
    Sup(sh1, sh2) = I0    e    Sup(sh1, sh3) = I1.
Costruzione su base random grid (Kafri-Keren, m=1): nessuna espansione,
il nero si ricostruisce esatto, il bianco resta "grigio" (probabilistico).

Uso:
    python genera_mvcs.py                     # usa due lettere di default
    python genera_mvcs.py I0.png I1.png       # usa le tue immagini
"""
import argparse
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager


def carica_segreto(percorso, size=None, soglia=128):
    """Apre un'immagine, la porta in bianco/nero e restituisce una matrice
    con 1 = nero, 0 = bianco. Se size e' dato, la ridimensiona a size x size."""
    img = Image.open(percorso).convert("L")
    if size is not None:
        img = img.resize((size, size), Image.LANCZOS)
    pixel = np.asarray(img)
    return (pixel < soglia).astype(np.uint8)   # scuro -> 1 (nero)


def Shr(I0, I1):
    """Shr(I0, I1): genera le tre share sh1, sh2, sh3."""
    n_righe, n_colonne = I0.shape
    sh1 = np.zeros((n_righe, n_colonne), dtype=np.uint8)
    sh2 = np.zeros((n_righe, n_colonne), dtype=np.uint8)
    sh3 = np.zeros((n_righe, n_colonne), dtype=np.uint8)
    for i in range(n_righe):
        for j in range(n_colonne):
            sh1[i, j] = np.random.randint(2)          # bit casuale in {0,1}
            if I0[i, j] == 0:                         # (sh1,sh2) = KK-share di I0
                sh2[i, j] = sh1[i, j]
            else:
                sh2[i, j] = 1 - sh1[i, j]
            if I1[i, j] == 0:                          # (sh1,sh3) = KK-share di I1
                sh3[i, j] = sh1[i, j]
            else:
                sh3[i, j] = 1 - sh1[i, j]
    return sh1, sh2, sh3


def Sup(a, b):
    """Sovrapposizione delle share = OR logico."""
    return (a | b).astype(np.uint8)


# ----- utilita' ----------------------------------------------------------
def lettera(ch, size):
    """Segreto di default: una lettera nera su sfondo bianco (1 = nero)."""
    fp = font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans", weight="bold"))
    font = ImageFont.truetype(fp, int(size * 0.9))
    img = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(img)
    bb = d.textbbox((0, 0), ch, font=font)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.text(((size - w) / 2 - bb[0], (size - h) / 2 - bb[1]), ch, fill=255, font=font)
    return (np.asarray(img) > 127).astype(np.uint8)


def salva(bits, percorso, scala=8):
    """Salva una matrice 0/1 come PNG (1 -> nero), ingrandita di 'scala'."""
    img = Image.fromarray(np.where(bits == 1, 0, 255).astype(np.uint8), mode="L")
    img = img.resize((bits.shape[1] * scala, bits.shape[0] * scala), Image.NEAREST)
    img.save(percorso)


def _mostra(ax, bits, titolo):
    ax.imshow(1 - bits, cmap="gray", vmin=0, vmax=1, interpolation="nearest")
    ax.set_title(titolo, fontsize=11)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_edgecolor("0.6")


# ----- main --------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Esempio visuale dello Scheme-2-MVCS.")
    ap.add_argument("immagini", nargs="*", help="due percorsi immagine: I0 I1 (opzionale)")
    ap.add_argument("--size", type=int, default=48, help="lato delle immagini in pixel")
    ap.add_argument("--seed", type=int, default=7, help="seme del generatore casuale")
    ap.add_argument("--out", default=".", help="cartella di output")
    args = ap.parse_args()

    np.random.seed(args.seed)

    if len(args.immagini) == 2:
        I0 = carica_segreto(args.immagini[0], size=args.size)
        I1 = carica_segreto(args.immagini[1], size=args.size)
    else:
        I0 = lettera("F", args.size)
        I1 = lettera("L", args.size)

    sh1, sh2, sh3 = Shr(I0, I1)
    sup12, sup13 = Sup(sh1, sh2), Sup(sh1, sh3)

    out = args.out.rstrip("/")
    os.makedirs(out or ".", exist_ok=True)
    for nome, m in [("I0", I0), ("I1", I1), ("sh1", sh1), ("sh2", sh2),
                    ("sh3", sh3), ("sup_12", sup12), ("sup_13", sup13)]:
        salva(m, f"{out}/mvcs_{nome}.png")

    fig, axs = plt.subplots(2, 4, figsize=(9.5, 5.0))
    _mostra(axs[0, 0], I0, r"segreto $I_0$")
    _mostra(axs[0, 1], sh1, r"$sh_1$")
    _mostra(axs[0, 2], sh2, r"$sh_2$")
    _mostra(axs[0, 3], sup12, r"$\mathrm{Sup}(sh_1,sh_2)=I_0$")
    _mostra(axs[1, 0], I1, r"segreto $I_1$")
    _mostra(axs[1, 1], sh1, r"$sh_1$ (la stessa)")
    _mostra(axs[1, 2], sh3, r"$sh_3$")
    _mostra(axs[1, 3], sup13, r"$\mathrm{Sup}(sh_1,sh_3)=I_1$")
    fig.tight_layout()
    fig.savefig(f"{out}/mvcs_esempio.png", dpi=200)
    print("Fatto. Immagini salvate in:", out or ".")

if __name__ == "__main__":
    main()