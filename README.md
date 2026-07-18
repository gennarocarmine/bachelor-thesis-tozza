# bachelor-s-thesis-tozza

Python implementation of the **V2PC** protocol (_Visual Two-Party Computation_) by D'Arco
and De Prisco: two parties evaluate a boolean function on their private inputs using only
**transparencies to overlay**, with no keys and no encryption algorithms in the computation
phase. A computer is needed only once, to prepare the transparencies; from then on the
computation is pure stacking of sheets, and the reading is done by the eye.

Repository of a Bachelor's thesis in Computer Science — University of Salerno.
Candidate: **Gennaro Carmine Tozza** · Advisor: **Prof. Roberto De Prisco**.

---

## Main Reference Papers

The protocol implemented here:

- P. D'Arco, R. De Prisco. _Secure computation without computers_. **Theoretical Computer
  Science 651 (2016) 11–36.** [doi:10.1016/j.tcs.2016.08.003](https://doi.org/10.1016/j.tcs.2016.08.003)
  — this is the V2PC protocol and the example reproduced here.
- P. D'Arco, R. De Prisco. _Secure two-party computation: a visual way_. ICITS 2013, LNCS
  8317, 18–38. [doi:10.1007/978-3-319-04268-8_2](https://doi.org/10.1007/978-3-319-04268-8_2)
  (open-access preprint: [eprint.iacr.org/2013/257](https://eprint.iacr.org/2013/257)) —
  earlier version of the protocol.

## Requirements

Python 3.10+ and the libraries listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

(NumPy, Pillow, Flask, matplotlib)

## Command-line usage

From the `code/v2pc-protocol` folder:

```bash
# evaluate a function on an input (prints the true result and the visual one)
python3 cli.py evaluate "(x1|y1) & ((x2&y2) & (x3|y3))" \
        --input x1=0,y1=1,x2=1,y2=1,x3=1,y3=0

# save the printable transparencies used for an input
python3 cli.py shares "x1 & y1" --input x1=1,y1=1 --out share

# multi-output function: half-adder (sum and carry)
python3 cli.py multi "x ^ y" "x & y" --input x=1,y=1
```

**Function syntax.** Operators `&` (AND), `|` (OR), `^` (XOR), `~` (NOT), with parentheses;
the NAND, NOR and XNOR gates are written as `~(a&b)`, `~(a|b)`, `~(a^b)`. By convention,
variables starting with `x` are Alice's inputs, those starting with `y` are Bob's.

**Options.** `--size` is the side of the block that encodes a value (default 32); `--seed`
fixes the randomness of the construction, to reproduce exactly the same shares.

## Web demo

From the `code/v2pc-protocol/` folder:

```bash
python3 app.py
```

then open **http://127.0.0.1:5000**. The demo has two pages: a share generator, which shows
the transparency of each wire, the circuit drawing, and the reconstructed output image; and
a two-party example, in which the other party's inputs stay hidden and the confidentiality
of the protocol can be observed. The transparencies can be downloaded and printed, to return
to the physical nature of the protocol.

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
