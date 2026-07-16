"""
Esempio concreto di una porta visuale (VGESS) per una porta AND, nello stile
del paper "Secure computation without computers".

Valori dei fili come immagini: 0 = blocco bianco, 1 = blocco nero.
Due istanze dello Scheme-2-MVCS (A e B), bit di permutazione b=0.
Si mostrano due valutazioni con lo stesso input destro (v2=1): il pointer bit
p = v1 xor b seleziona quale meta' della share destra sovrapporre a sh1, e da'
due uscite diverse. Con AND: G(1,1)=1 (nero), G(0,1)=0 (bianco/grigio).
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

np.random.seed(3)
T = 12          # lato del blocco-valore
PW = 5          # larghezza del pittogramma del pointer bit


def Shr(I0, I1):
    r, c = I0.shape
    sh1 = np.random.randint(0, 2, size=(r, c)).astype(np.uint8)
    sh2 = np.where(I0 == 0, sh1, 1 - sh1).astype(np.uint8)
    sh3 = np.where(I1 == 0, sh1, 1 - sh1).astype(np.uint8)
    return sh1, sh2, sh3


def Sup(a, b):
    return (a | b).astype(np.uint8)


# valori come immagini: 0 = bianco (zeros), 1 = nero (ones)
O = np.zeros((T, T), np.uint8)     # Image(0)
I = np.ones((T, T), np.uint8)      # Image(1)

# AND: (G00,G01)=(0,0) -> istanza A ; (G10,G11)=(0,1) -> istanza B
sh1A, sh2A, sh3A = Shr(O, O)
sh1B, sh2B, sh3B = Shr(O, I)

b = 0
# share destra per v2=1 (b=0): meta' A poi meta' B  ->  sh3A | sh3B
right_v1 = np.hstack([sh3A, sh3B])


def pointer_block(bit):
    return np.full((T, PW), bit, np.uint8)


def left_share(sh1, p):
    return np.hstack([pointer_block(p), sh1])


def show(ax, bits, title):
    ax.imshow(1 - bits, cmap="gray", vmin=0, vmax=1, interpolation="nearest")
    ax.set_title(title, fontsize=10)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_edgecolor("0.6")


def op(ax, simbolo):
    ax.text(0.5, 0.5, simbolo, ha="center", va="center", fontsize=20)
    ax.axis("off")


fig, axs = plt.subplots(2, 5, figsize=(11, 4.6),
                        gridspec_kw={"width_ratios": [1.6, 0.3, 2.0, 0.3, 1.0]})

# ---------------- riga 1: v1=1, v2=1  ->  AND = 1 ----------------
L1 = left_share(sh1B, 1)
show(axs[0, 0], L1, r"share sinistra  $v_1=1$   ($p{=}1 \,\|\, sh_1^B$)")
axs[0, 0].axvline(PW - 0.5, color="red", lw=1.2)
op(axs[0, 1], "+")
show(axs[0, 2], right_v1, r"share destra  $v_2=1$   ($sh_3^A \,\|\, sh_3^B$)")
axs[0, 2].add_patch(Rectangle((T - 0.5, -0.5), T, T, fill=False, edgecolor="red", lw=2))
op(axs[0, 3], "=")
show(axs[0, 4], Sup(sh1B, sh3B), r"$\mathrm{Sup}=I_{G(1,1)}=I_1$  (uscita 1)")

# ---------------- riga 2: v1=0, v2=1  ->  AND = 0 ----------------
L0 = left_share(sh1A, 0)
show(axs[1, 0], L0, r"share sinistra  $v_1=0$   ($p{=}0 \,\|\, sh_1^A$)")
axs[1, 0].axvline(PW - 0.5, color="red", lw=1.2)
op(axs[1, 1], "+")
show(axs[1, 2], right_v1, r"share destra  $v_2=1$   ($sh_3^A \,\|\, sh_3^B$)")
axs[1, 2].add_patch(Rectangle((-0.5, -0.5), T, T, fill=False, edgecolor="red", lw=2))
op(axs[1, 3], "=")
show(axs[1, 4], Sup(sh1A, sh3A), r"$\mathrm{Sup}=I_{G(0,1)}=I_0$  (uscita 0)")

fig.tight_layout()
fig.savefig("vgess_porta.png", dpi=200)
print("ok")