"""
(2,2) Visual Cryptography Scheme (VCS) - Naor & Shamir, 1994.

Questo codice segue passo-passo lo pseudocodice:

    Shr(I):
      For every i, j:
        Choose uniformly at random r_{i,j} in {0,1}
        Use row k of C_{I(i,j), r_{i,j}} to set sh_k(i,j), for k = 1, 2
      Output (sh1, sh2)

    Rec(sh1, sh2):
      Return I = Sup(sh1, sh2)

IDEA: l'immagine segreta (bianco/nero) viene divisa in 2 fogli ("share").
Una share da sola sembra rumore; sovrapponendole (Sup) ricompare il segreto.
Ogni pixel del segreto diventa una riga di 2 sottopixel (pixel expansion m = 2).

"""

import numpy as np
from PIL import Image

# Le collezioni C[I][r] dello pseudocodice.
# - I = valore del pixel segreto: 0 = bianco, 1 = nero
# - r = bit scelto a caso in {0, 1}
# Ogni matrice ha 2 righe (riga 0 -> share 1, riga 1 -> share 2)
# e 2 colonne (i 2 sottopixel).  1 = nero, 0 = bianco.
C = {
    0: [  # pixel BIANCO -> le due righe sono UGUALI
        np.array([[1, 0],
                  [1, 0]], dtype=np.uint8),   # r = 0
        np.array([[0, 1],
                  [0, 1]], dtype=np.uint8),   # r = 1
    ],
    1: [  # pixel NERO -> le due righe sono OPPOSTE
        np.array([[1, 0],
                  [0, 1]], dtype=np.uint8),   # r = 0
        np.array([[0, 1],
                  [1, 0]], dtype=np.uint8),   # r = 1
    ],
}


def carica_segreto(percorso, soglia=128):
    """Apre un'immagine e la rende bianco/nero. Ritorna 1 = nero, 0 = bianco."""
    img = Image.open(percorso).convert("L")          # scala di grigi
    pixel = np.asarray(img)
    return (pixel < soglia).astype(np.uint8)         # scuro -> 1 (nero)


def Shr(I):
    """Shr(I): divide il segreto I nelle due share sh1, sh2."""
    n_righe, n_colonne = I.shape

    # Ogni pixel diventa 2 sottopixel: le share sono larghe il doppio.
    sh1 = np.zeros((n_righe, 2 * n_colonne), dtype=np.uint8)
    sh2 = np.zeros((n_righe, 2 * n_colonne), dtype=np.uint8)

    for i in range(n_righe):
        for j in range(n_colonne):
            r = np.random.randint(2)        # r_{i,j} a caso in {0, 1}
            M = C[I[i, j]][r]               # scelgo la matrice C_{I, r}
            sh1[i, 2*j:2*j+2] = M[0]        # riga 0 -> share 1
            sh2[i, 2*j:2*j+2] = M[1]        # riga 1 -> share 2

    return sh1, sh2


def Sup(sh1, sh2):
    """Sup: sovrapposizione delle share. Nero se nero in almeno una share (OR)."""
    return sh1 | sh2


def Rec(sh1, sh2):
    """Rec(sh1, sh2): ricostruisce il segreto sovrapponendo le share."""
    return Sup(sh1, sh2)


def salva(bitmap, percorso):
    """Salva un array (1 = nero, 0 = bianco) come immagine."""
    immagine = np.where(bitmap == 1, 0, 255).astype(np.uint8)  # 1->nero 0->bianco
    Image.fromarray(immagine).convert("L").save(percorso)



# --- Programma principale ---------------------------------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        I = carica_segreto(sys.argv[1])     # immagine da riga di comando
    else:
        print("Nessuna immagine fornita.")

    sh1, sh2 = Shr(I)
    ricostruito = Rec(sh1, sh2)

    salva(sh1, "share1.png")
    salva(sh2, "share2.png")
    salva(ricostruito, "recovered.png")

    print("Creati: share1.png, share2.png, recovered.png")
