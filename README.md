# bachelor-s-thesis-tozza

Implementazione in Python del protocollo **V2PC** (_Visual Two-Party Computation_) di D'Arco e De Prisco.
Python implementation of the **V2PC** protocol (_Visual Two-Party Computation_) by D'Arco and De Prisco.

Repository of a Bachelor's thesis in Computer Science — University of Salerno.
Candidate: **Gennaro Carmine Tozza** · Advisor: **Prof. Roberto De Prisco**.

## Indice · Table of contents

**[Italiano](#italiano)**

- [Paper di riferimento](#paper-di-riferimento)
- [Installazione](#installazione)
- [Uso da riga di comando](#uso-da-riga-di-comando)
- [Demo web](#demo-web)
- [Note](#note)
- [Documenti](#documenti)

**[English](#english)**

- [Main reference papers](#main-reference-papers)
- [Installation](#installation)
- [Command-line usage](#command-line-usage)
- [Web demo](#web-demo)
- [Notes](#notes)
- [Documents](#documents)

---

# Italiano

Due parti calcolano una funzione booleana sui propri input privati usando soltanto
**trasparenze da sovrapporre**, senza chiavi e senza algoritmi di cifratura nella fase di
calcolo. Il computer serve una sola volta, per preparare le trasparenze; da lì in poi il
calcolo è pura sovrapposizione di fogli, e la lettura la fa l'occhio.

## Paper di riferimento

Il protocollo implementato qui:

- P. D'Arco, R. De Prisco. _Secure computation without computers_. **Theoretical Computer
  Science 651 (2016) 11–36.** [doi:10.1016/j.tcs.2016.08.003](https://doi.org/10.1016/j.tcs.2016.08.003)
  — è il protocollo V2PC e l'esempio riprodotto qui.
- P. D'Arco, R. De Prisco. _Secure two-party computation: a visual way_. ICITS 2013, LNCS
  8317, 18–38. [doi:10.1007/978-3-319-04268-8_2](https://doi.org/10.1007/978-3-319-04268-8_2)
  (preprint ad accesso aperto: [eprint.iacr.org/2013/257](https://eprint.iacr.org/2013/257))
  — versione precedente del protocollo.

## Installazione

Serve Python 3.10 o successivo.

**. Clona il repository**

```bash
git clone https://github.com/gennarocarmine/bachelor-s-thesis-tozza.git
cd bachelor-s-thesis-tozza
```

Scarica il progetto ed entra nella cartella appena creata.

**. Installa le dipendenze**

```bash
pip install -r requirements.txt
```

Installa NumPy, Pillow, Flask e matplotlib.

## Uso da riga di comando

Tutti i comandi si lanciano dalla cartella `code/v2pc-protocol`.

```bash
python3 cli.py evaluate "(x1|y1) & ((x2&y2) & (x3|y3))" \
        --input x1=0,y1=1,x2=1,y2=1,x3=1,y3=0
```

Valuta la funzione sull'input indicato e stampa il risultato vero accanto a quello ottenuto
per via visuale, segnalando se coincidono.

```bash
python3 cli.py shares "x1 & y1" --input x1=1,y1=1 --out share
```

Salva nella cartella `share` le trasparenze usate per quell'input, come immagini pronte da
stampare su lucido.

```bash
python3 cli.py multi "x ^ y" "x & y" --input x=1,y=1
```

Valuta una funzione a più bit di uscita, una espressione per ciascun bit: qui un half-adder,
con la somma e il riporto.

**Sintassi delle funzioni.** Operatori `&` (AND), `|` (OR), `^` (XOR), `~` (NOT), con le
parentesi; le porte NAND, NOR e XNOR si scrivono come `~(a&b)`, `~(a|b)`, `~(a^b)`. Per
convenzione le variabili che iniziano per `x` sono input di Alice, quelle che iniziano per
`y` input di Bob.

**Opzioni.** `--size` è il lato del blocco che codifica un valore (default 32); `--seed`
fissa la casualità della costruzione, per riprodurre esattamente le stesse share.

## Demo web

```bash
python3 app.py
```

Da lanciare anch'esso dalla cartella `code/v2pc-protocol`. Avvia il server locale: apri poi
**http://127.0.0.1:5000**. La demo ha due pagine: un generatore di share, che mostra la
trasparenza di ogni filo, il disegno del circuito e l'immagine di uscita ricostruita; e un
esempio a due parti, in cui gli input dell'altra parte restano nascosti e si può osservare la
riservatezza del protocollo. Le trasparenze si possono scaricare e stampare, per tornare alla
natura fisica del protocollo.

## Note

- **Correttezza e dimensione delle immagini.** La ricostruzione del bianco è probabilistica:
  se le immagini sono troppo piccole, un'uscita che vale zero può annerirsi del tutto ed essere
  letta come uno. La dimensione (`--size`) va scelta abbastanza grande, e quanto grande dipende
  dal **numero di porte** del circuito. Il valore predefinito 32 lascia un ampio margine per
  circuiti piccoli.
- **Il seme (`--seed`).** La costruzione delle share è casuale, quindi ogni esecuzione produce
  share diverse. Fissare il seme rende la costruzione riproducibile (stesse share, stesse
  immagini); non incide sulla correttezza, serve solo a riprodurre esempi e figure.
- **Limiti.** La dimensione delle share cresce esponenzialmente con la profondità del circuito,
  quindi il protocollo è pratico solo per circuiti poco profondi; la sicurezza è dimostrata nel
  modello semi-onesto.

## Documenti

La tesi completa (in italiano) è in [`docs/main.pdf`](docs/main.pdf).

---

# English

Two parties evaluate a boolean function on their private inputs using only **transparencies
to overlay**, with no keys and no encryption algorithms in the computation phase. A computer
is needed only once, to prepare the transparencies; from then on the computation is pure
stacking of sheets, and the reading is done by the eye.

## Main reference papers

The protocol implemented here:

- P. D'Arco, R. De Prisco. _Secure computation without computers_. **Theoretical Computer
  Science 651 (2016) 11–36.** [doi:10.1016/j.tcs.2016.08.003](https://doi.org/10.1016/j.tcs.2016.08.003)
  — this is the V2PC protocol and the example reproduced here.
- P. D'Arco, R. De Prisco. _Secure two-party computation: a visual way_. ICITS 2013, LNCS
  8317, 18–38. [doi:10.1007/978-3-319-04268-8_2](https://doi.org/10.1007/978-3-319-04268-8_2)
  (open-access preprint: [eprint.iacr.org/2013/257](https://eprint.iacr.org/2013/257)) —
  earlier version of the protocol.

## Installation

Python 3.10 or later is required.

**. Clone the repository**

```bash
git clone https://github.com/gennarocarmine/bachelor-s-thesis-tozza.git
cd bachelor-s-thesis-tozza
```

Downloads the project and enters the folder just created.

**. Install the dependencies**

```bash
pip install -r requirements.txt
```

Installs NumPy, Pillow, Flask and matplotlib.

## Command-line usage

All commands are run from the `code/v2pc-protocol` folder.

```bash
python3 cli.py evaluate "(x1|y1) & ((x2&y2) & (x3|y3))" \
        --input x1=0,y1=1,x2=1,y2=1,x3=1,y3=0
```

Evaluates the function on the given input and prints the true result next to the one obtained
visually, reporting whether they match.

```bash
python3 cli.py shares "x1 & y1" --input x1=1,y1=1 --out share
```

Saves into the `share` folder the transparencies used for that input, as images ready to be
printed on acetate.

```bash
python3 cli.py multi "x ^ y" "x & y" --input x=1,y=1
```

Evaluates a multi-output function, one expression per output bit: here a half-adder, with the
sum and the carry.

**Function syntax.** Operators `&` (AND), `|` (OR), `^` (XOR), `~` (NOT), with parentheses;
the NAND, NOR and XNOR gates are written as `~(a&b)`, `~(a|b)`, `~(a^b)`. By convention,
variables starting with `x` are Alice's inputs, those starting with `y` are Bob's.

**Options.** `--size` is the side of the block that encodes a value (default 32); `--seed`
fixes the randomness of the construction, to reproduce exactly the same shares.

## Web demo

```bash
python3 app.py
```

Also run from the `code/v2pc-protocol` folder. It starts the local server: then open
**http://127.0.0.1:5000**. The demo has two pages: a share generator, which shows the
transparency of each wire, the circuit drawing, and the reconstructed output image; and a
two-party example, in which the other party's inputs stay hidden and the confidentiality of
the protocol can be observed. The transparencies can be downloaded and printed, to return to
the physical nature of the protocol.

## Notes

- **Correctness and image size.** The reconstruction of white is probabilistic: if the images
  are too small, an output that is zero may turn completely black and be read as one. The size
  (`--size`) must be chosen large enough; how large depends on the **number of gates** of the
  circuit. The default value 32 leaves a wide margin for small circuits.
- **The seed (`--seed`).** The construction of the shares is random, so every run produces
  different shares. Fixing the seed makes the construction reproducible (same shares, same
  images); it does not affect correctness, it only serves to reproduce examples and figures.
- **Limits.** The size of the shares grows exponentially with the depth of the circuit, so the
  protocol is practical only for shallow circuits; security is proven in the semi-honest model.

## Documents

The full thesis (in Italian) is in [`docs/main.pdf`](docs/main.pdf).
