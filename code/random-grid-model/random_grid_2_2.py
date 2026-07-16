"""
Random Grid (2,2) - algoritmo di Kafri e Keren, 1987.

Questo codice segue passo-passo lo pseudocodice:

    ShrRG(I):   # cifratura: NESSUNA espansione dei pixel
      Per ogni pixel (i, j):
        R1(i, j) <- bit casuale in {0, 1}
        Se I(i, j) = 0 (bianco):  R2(i, j) <- R1(i, j)
        Se I(i, j) = 1 (nero):    R2(i, j) <- 1 - R1(i, j)
      Return (R1, R2)

    Rec(R1, R2):   # ricostruzione: solo sovrapposizione
      Return I = Sup(R1, R2)

IDEA: il segreto (bianco/nero) viene diviso in due "griglie" R1 e R2 della
STESSA dimensione del segreto (a differenza del VCS, qui non si raddoppia nulla).
Ogni griglia da sola sembra rumore; sovrapponendole (Sup = OR) ricompare il
segreto: le zone nere tornano nere, le zone bianche restano grigie (rumore).

Serve: pip install numpy pillow
"""

import numpy as np
from PIL import Image


def carica_segreto(percorso, soglia=128):
    """Apre un'immagine e la rende bianco/nero. Ritorna 1 = nero, 0 = bianco."""
    img = Image.open(percorso).convert("L")          # scala di grigi
    pixel = np.asarray(img)
    return (pixel < soglia).astype(np.uint8)         # scuro -> 1 (nero)


def ShrRG(I):
    """ShrRG(I): divide il segreto I nelle due griglie R1, R2 (stessa dimensione)."""
    n_righe, n_colonne = I.shape

    # Le griglie hanno la STESSA dimensione del segreto (nessuna espansione).
    R1 = np.zeros((n_righe, n_colonne), dtype=np.uint8)
    R2 = np.zeros((n_righe, n_colonne), dtype=np.uint8)

    for i in range(n_righe):
        for j in range(n_colonne):
            R1[i, j] = np.random.randint(2)      # bit casuale in {0, 1}
            if I[i, j] == 0:
                # pixel BIANCO -> R2 uguale a R1
                R2[i, j] = R1[i, j]
            else:
                # pixel NERO -> R2 opposto a R1
                R2[i, j] = 1 - R1[i, j]

    return R1, R2


def Sup(R1, R2):
    """Sup: sovrapposizione. Nero se nero in almeno una griglia (OR)."""
    return R1 | R2


def Rec(R1, R2):
    """Rec(R1, R2): ricostruisce il segreto sovrapponendo le griglie."""
    return Sup(R1, R2)


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
        sys.exit(1)

    R1, R2 = ShrRG(I)
    ricostruito = Rec(R1, R2)

    salva(R1, "rg_share1.png")
    salva(R2, "rg_share2.png")
    salva(ricostruito, "rg_recovered.png")

    print("Creati: rg_share1.png, rg_share2.png, rg_recovered.png")
