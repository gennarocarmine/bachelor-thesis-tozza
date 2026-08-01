# bachelor-thesis-tozza

Repository of a Bachelor's thesis in Computer Science — University of Salerno.
Candidate: **Gennaro Carmine Tozza**. Advisor: **Prof. Roberto De Prisco**.

## Indice - Table of contents

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

# 🇮🇹 Italiano

Implementazione in Python del protocollo **V2PC** (_Visual Two-Party
Computation_) di D'Arco e De Prisco.

Due parti calcolano una funzione booleana sui propri input privati mediante
**trasparenze da sovrapporre**. Il programma genera inizialmente tutte le
possibili share senza conoscere i valori degli input. In seguito seleziona le
share corrispondenti ai valori scelti e ricostruisce il risultato mediante
sovrapposizione.

## Paper di riferimento

Il protocollo implementato è descritto nei seguenti lavori:

- P. D'Arco, R. De Prisco. _Secure computation without computers_.
  **Theoretical Computer Science 651 (2016) 11–36.**
  [doi:10.1016/j.tcs.2016.08.003](https://doi.org/10.1016/j.tcs.2016.08.003)
  — versione principale del protocollo V2PC e fonte dell'esempio riprodotto.
- P. D'Arco, R. De Prisco. _Secure two-party computation: a visual way_.
  ICITS 2013, LNCS 8317, 18–38.
  [doi:10.1007/978-3-319-04268-8_2](https://doi.org/10.1007/978-3-319-04268-8_2)
  (preprint ad accesso aperto:
  [eprint.iacr.org/2013/257](https://eprint.iacr.org/2013/257)) — versione
  precedente del protocollo.

## Installazione

È richiesto Python 3.9 o successivo.

**1. Clona il repository**

```bash
git clone https://github.com/gennarocarmine/bachelor-thesis-tozza.git
cd bachelor-thesis-tozza
```

**2. Crea e attiva un ambiente virtuale**

Su macOS o Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Su Windows:

```powershell
py -m venv .venv
.venv\Scripts\activate
```

**3. Installa dipendenze e programma**

I comandi seguenti devono essere eseguiti dalla radice del repository:

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install --no-deps -e ./code/v2pc-python
```

L'ultimo comando installa l'eseguibile `v2pc` usando il codice locale. L'opzione
`--no-deps` evita di installare due volte le dipendenze già lette dal
`requirements.txt` principale.

**4. Verifica l'installazione**

```bash
v2pc --help
```

L'output deve mostrare i comandi `evaluate`, `construct`, `transfer`,
`reconstruct` e `serve`.

## Uso da riga di comando

La sintassi delle formule usa:

- `&` per AND;
- `|` per OR;
- `^` per XOR;
- `~` per NOT;
- parentesi per indicare l'ordine delle operazioni.

NAND, NOR e XNOR si scrivono rispettivamente come `~(a&b)`, `~(a|b)` e
`~(a^b)`. Per convenzione, le variabili che iniziano con `x` appartengono ad
Alice e quelle che iniziano con `y` appartengono a Bob.

### Esecuzione completa in tre fasi

La costruzione genera le due alternative 0 e 1 di ogni occorrenza di input,
senza utilizzare i valori di Alice e Bob:

```bash
v2pc construct "(x1|y1)&((x2&y2)&(x3|y3))" \
  --output costruzione --side 32 --seed 7
```

La distribuzione conserva una sola share per ogni ingresso. Le share di Alice
sono consegnate direttamente; per quelle di Bob viene simulata localmente la
selezione tramite _oblivious transfer_:

```bash
v2pc transfer --source costruzione \
  --input "x1=0,y1=1,x2=1,y2=1,x3=1,y3=0" \
  --output trasferimento
```

La ricostruzione usa soltanto il pacchetto trasferito. Non riceve
l'assegnamento degli input e non può accedere alle alternative scartate:

```bash
v2pc reconstruct --source trasferimento
```

I risultati e le immagini intermedie vengono salvati nella cartella
`trasferimento/reconstruction`.

### Valutazione immediata

Per eseguire localmente le tre fasi con un solo comando:

```bash
v2pc evaluate "(x1|y1)&((x2&y2)&(x3|y3))" \
  --input "x1=0,y1=1,x2=1,y2=1,x3=1,y3=0" \
  --side 32 --seed 7
```

Il comando confronta il valore ricostruito visualmente con il risultato
booleano della formula.

### Opzioni principali

Le opzioni disponibili dipendono dal comando:

- `--side`, disponibile con `construct` ed `evaluate`, indica il lato in pixel
  dell'immagine di base. Il valore predefinito è 32;
- `--seed`, disponibile con `construct` ed `evaluate`, rende riproducibile la
  costruzione casuale. Se viene omesso, viene utilizzata nuova casualità;
- `--output`, disponibile nelle tre fasi separate, indica la cartella in cui
  salvare gli artefatti prodotti;
- `--scale`, disponibile con `construct`, `transfer` e `reconstruct`, controlla
  l'ingrandimento delle immagini esportate.

Per l'elenco completo:

```bash
v2pc NOME_COMANDO --help
```

Le share esportate includono i pointer bit come blocchi `1×2` anteposti alle
rispettive immagini.

## Demo web

Con l'ambiente virtuale attivo, eseguire dalla radice del repository:

```bash
v2pc serve
```

Aprire quindi [http://127.0.0.1:5000](http://127.0.0.1:5000) nel browser.
Per arrestare il server, premere `Ctrl+C` nel terminale.

La demo web:

- riconosce automaticamente le variabili della formula e crea i selettori 0/1;
- genera tutte le alternative senza usare i valori selezionati;
- distingue la consegna diretta delle share di Alice dall'OT simulato per Bob;
- ricostruisce il risultato e lo confronta con il valore booleano;
- visualizza il circuito completo con porte, share e pointer bit;
- permette di scaricare il circuito visualizzato come immagine PNG;
- produce un archivio contenente tutte le alternative, i PNG e un PDF A4
  ritagliabile, con il reticolo dei pixel logici come nelle tavole del paper,
  da preparare prima di conoscere gli input;
- produce un kit di stampa con le share trasferite, i PNG, un PDF A4 a 300 dpi
  e le istruzioni per taglio, allineamento e sovrapposizione.

CLI e demo web utilizzano lo stesso nucleo del protocollo.

## Note

- **Oblivious transfer.** La CLI e la demo simulano localmente la selezione
  delle share di Bob. Non implementano un OT fisico o un protocollo OT di rete.
- **Pointer bit.** Il pointer della porta corrente è leggibile in chiaro,
  mentre i pointer da propagare sono condivisi mediante uno schema
  deterministico `(2,2)`. I blocchi sono collocati accanto alla share come nel
  paper; nelle share destre ogni pointer precede la metà a cui appartiene.
- **Correttezza e dimensione delle immagini.** Il nero viene ricostruito
  esattamente, mentre la lettura del bianco è probabilistica. Immagini troppo
  piccole possono produrre un falso positivo; il lato delle immagini deve
  quindi essere scelto in funzione della profondità del circuito.
- **Limiti.** La dimensione delle share cresce rapidamente con la profondità
  della formula. Il protocollo è quindi adatto soprattutto a circuiti poco
  profondi ed è analizzato nel modello semi-onesto.

## Documenti

La tesi completa, in italiano, è disponibile in
[`docs/main.pdf`](docs/main.pdf).

---

# 🇬🇧 English

Python implementation of the **V2PC** protocol (_Visual Two-Party
Computation_) by D'Arco and De Prisco.

Two parties evaluate a Boolean function on their private inputs using
**transparencies that are physically overlaid**. The program initially
generates every possible share without knowing the input values. It then
selects the shares corresponding to the chosen inputs and reconstructs the
result through superposition.

## Main reference papers

The implemented protocol is described in:

- P. D'Arco, R. De Prisco. _Secure computation without computers_.
  **Theoretical Computer Science 651 (2016) 11–36.**
  [doi:10.1016/j.tcs.2016.08.003](https://doi.org/10.1016/j.tcs.2016.08.003)
  — the main V2PC protocol and the source of the reproduced example.
- P. D'Arco, R. De Prisco. _Secure two-party computation: a visual way_.
  ICITS 2013, LNCS 8317, 18–38.
  [doi:10.1007/978-3-319-04268-8_2](https://doi.org/10.1007/978-3-319-04268-8_2)
  (open-access preprint:
  [eprint.iacr.org/2013/257](https://eprint.iacr.org/2013/257)) — an earlier
  version of the protocol.

## Installation

Python 3.9 or later is required.

**1. Clone the repository**

```bash
git clone https://github.com/gennarocarmine/bachelor-thesis-tozza.git
cd bachelor-thesis-tozza
```

**2. Create and activate a virtual environment**

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
py -m venv .venv
.venv\Scripts\activate
```

**3. Install the dependencies and the program**

Run the following commands from the repository root:

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install --no-deps -e ./code/v2pc-python
```

The last command installs the `v2pc` executable from the local source.
`--no-deps` avoids reinstalling the dependencies already listed in the root
`requirements.txt`.

**4. Verify the installation**

```bash
v2pc --help
```

The output should list `evaluate`, `construct`, `transfer`, `reconstruct` and
`serve`.

## Command-line usage

Function syntax uses:

- `&` for AND;
- `|` for OR;
- `^` for XOR;
- `~` for NOT;
- parentheses to define evaluation order.

NAND, NOR and XNOR are written as `~(a&b)`, `~(a|b)` and `~(a^b)`. By
convention, variables beginning with `x` belong to Alice and variables
beginning with `y` belong to Bob.

### Complete three-phase execution

Construction generates both alternatives, 0 and 1, for every input occurrence
without using Alice's or Bob's values:

```bash
v2pc construct "(x1|y1)&((x2&y2)&(x3|y3))" \
  --output construction --side 32 --seed 7
```

Distribution keeps only one share for each input. Alice's shares are delivered
directly; Bob's selection through _oblivious transfer_ is simulated locally:

```bash
v2pc transfer --source construction \
  --input "x1=0,y1=1,x2=1,y2=1,x3=1,y3=0" \
  --output transfer
```

Reconstruction uses only the transferred package. It does not receive the
input assignment and cannot access the discarded alternatives:

```bash
v2pc reconstruct --source transfer
```

Results and intermediate images are saved in `transfer/reconstruction`.

### Immediate evaluation

To run all three phases locally with a single command:

```bash
v2pc evaluate "(x1|y1)&((x2&y2)&(x3|y3))" \
  --input "x1=0,y1=1,x2=1,y2=1,x3=1,y3=0" \
  --side 32 --seed 7
```

The command compares the visually reconstructed value with the Boolean result
of the formula.

### Main options

Available options depend on the command:

- `--side`, available for `construct` and `evaluate`, sets the side in pixels
  of the base image. The default is 32;
- `--seed`, available for `construct` and `evaluate`, makes the random
  construction reproducible. If omitted, fresh randomness is used;
- `--output`, available in the three separate phases, selects the directory in
  which generated artefacts are saved;
- `--scale`, available for `construct`, `transfer` and `reconstruct`, controls
  the enlargement of exported images.

For the complete list:

```bash
v2pc COMMAND_NAME --help
```

Exported shares include pointer bits as `1×2` blocks prepended to their images.

## Web demo

With the virtual environment active, run from the repository root:

```bash
v2pc serve
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in a browser. Press
`Ctrl+C` in the terminal to stop the server.

The web demo:

- detects formula variables and creates their 0/1 selectors automatically;
- generates every alternative without using the selected values;
- distinguishes Alice's direct delivery from Bob's simulated OT;
- reconstructs the result and compares it with the Boolean value;
- displays the complete circuit with gates, shares and pointer bits;
- downloads the displayed circuit as a PNG image;
- produces an archive containing every alternative, the PNG files and a
  cut-ready A4 PDF with the logical-pixel grid used in the paper's plates,
  prepared before the input values are known;
- produces a print kit containing the transferred shares, PNG files, a
  300-dpi A4 PDF and cutting, alignment and overlay instructions.

The CLI and web demo use the same protocol core.

## Notes

- **Oblivious transfer.** The CLI and demo simulate Bob's share selection
  locally. They do not implement a physical OT or a network OT protocol.
- **Pointer bit.** The current gate pointer is readable in the clear, while
  propagated pointers are shared using a deterministic `(2,2)` scheme. The
  blocks are placed next to their share as in the paper; in a right share,
  every pointer precedes the half to which it belongs.
- **Correctness and image size.** Black is reconstructed exactly, whereas
  white is read probabilistically. Images that are too small can produce a
  false positive; image size must therefore be chosen according to circuit
  depth.
- **Limits.** Share size grows rapidly with formula depth. The protocol is
  therefore mainly suitable for shallow circuits and is analysed in the
  semi-honest model.

## Documents

The full thesis, written in Italian, is available at
[`docs/main.pdf`](docs/main.pdf).
