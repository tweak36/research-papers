# Papers

A small collection of independent research papers by **William Duckworth**.

| # | Title | Topic | Date | PDF |
|---|-------|-------|------|-----|
| 1 | Deciphering Beale Cipher 1: A Comprehensive Statistical and Geographical Analysis | Cryptography / History | Feb 2025 | [PDF](papers/deciphering-beale-cipher-1.pdf) |
| 2 | Numerical Simulation of the Riemann Hypothesis: Impact of Zero Distribution on Prime Number Distribution | Number Theory / Computation | Jan 2025 | [PDF](papers/riemann-hypothesis-numerical-simulation.pdf) |
| 3 | AURORA-Mono (One-Piece) Rover Wheel — Build Specification | Mechanical / Aerospace Engineering | 2026 | [PDF](papers/aurora-mono-wheel-build-spec.pdf) |

---

## 1. Deciphering Beale Cipher 1

**[Read the PDF](papers/deciphering-beale-cipher-1.pdf)** · 7 pages

> A statistical and geographical analysis of Beale Cipher 1, proposing that two halves of the cipher encode latitude (**371221**) and longitude (**792316**) digits pointing into Bedford County, Virginia.

**Status:** Exploratory hobbyist analysis. The result depends on a chosen two-digit segmentation and on selecting which halves are read as which coordinate, so it is vulnerable to multiple-comparison concerns. It should be read as a thought experiment, not as a solved cipher.

**Highlights**

- Justifies a two-digit segmentation approach as historically plausible for a 19th-century cipher.
- Uses statistical modeling (accounting for digit correlations) to estimate the probability of meaningful DMS values appearing by chance.
- Cross-references the already-solved Cipher 2, which states that "Paper number '1' describes the exact locality of the vault."

---

## 2. Numerical Simulation of the Riemann Hypothesis

**[Read the PDF](papers/riemann-hypothesis-numerical-simulation.pdf)** · 13 pages

> A Python visualization of the Chebyshev function ψ(x) and an approximation of the prime counting function π(x) under two scenarios: (a) all non-trivial zeros of ζ(s) on the critical line Re(s) = 1/2, and (b) hypothetical off-critical zeros added.

**Status:** Educational simulation, not original research. The "on-critical" zeros use a uniform-spacing approximation (γₙ ≈ 14.1347 + (n−1)·20.72) rather than true Riemann zero locations, and the "off-critical" zeros are fabricated for contrast. The plots are useful for building intuition about why RH matters for the regularity of primes; they are not evidence for or against the conjecture.

**Highlights**

- Includes the full Python source used to generate the simulations and plots (NumPy + Matplotlib) — run the code and it reproduces every figure in the paper.
- Side-by-side ψ(x) and π(x) curves under both zero distributions, with MAE / RMSE reported.
- Suitable as a teaching aid or self-study companion to a chapter on analytic number theory.

---

## 3. AURORA-Mono (One-Piece) Rover Wheel — Build Specification

**[Read the PDF](papers/aurora-mono-wheel-build-spec.pdf)** · 4 pages

> A paper design study for a one-piece composite rover wheel engineered to the MicroChariot interface envelope. The design pairs a carbon-nanotube-reinforced PEKK structural cage with a silicon-carbide-filled PEKK wear tread, joined by a co-molded mechanical and chemical bond.

**Status:** Paper design only. No prototype has been built or tested. Dimensions, material choices, and process windows are derived from published PEKK / CNT/CF data sheets and design intent — they have not been validated by FEA, autoclave trials, NDI, or any physical test. The document is a specification of design intent, not a qualified part.

**Highlights**

- **Envelope:** 18.000 in OD × 8.000 in wide, MicroChariot-compliant hub pattern with full keep-out compliance.
- **Sandwich rim wall:** 1.20 mm skins over a 7.00 mm helical-rib core (48 ribs at ±35°, X-brace lattice).
- **Hub torque web:** 6 internal composite web-spokes (5.0 → 3.0 mm taper) with triangular lightening pockets.
- **Tread:** integral SiC-PEKK chevron lugs in two staggered rows, 75–80% void ratio, with co-molded mechanical anti-peel keys and same-family chemical bonding at 355–365 °C.
- **Mass target (design intent):** 2.21–2.30 kg, with ~80–120 g optimization margin identified.
- Includes tolerances, a proposed manufacturing sequence (additive core → autoclave skins → machining → compression-molded tread → top-coat → NDI), and a full critical-dimensions table.

**Open work before this would be a real engineering artifact:** FEA on the rib lattice under lunar loading, thermal-cycling analysis against PEKK Tg margins, mass calculation derivation, prototype build and bench test.

---

## Repository layout

```
.
├── README.md
└── papers/
    ├── deciphering-beale-cipher-1.pdf
    ├── riemann-hypothesis-numerical-simulation.pdf
    └── aurora-mono-wheel-build-spec.pdf
```

## Citing

If you reference any of these papers, please cite as:

> Duckworth, W. *Deciphering Beale Cipher 1: A Comprehensive Statistical and Geographical Analysis.* 2025.

> Duckworth, W. *Numerical Simulation of the Riemann Hypothesis: Impact of Zero Distribution on Prime Number Distribution.* 2025.

> Duckworth, W. *AURORA-Mono (One-Piece) Rover Wheel — Build Specification, Rev 1.0.* 2026.

## License

Unless otherwise stated, the papers in this repository are released under the
[Creative Commons Attribution 4.0 International License (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
