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

> A robust analysis of Beale Cipher 1, arguing that it encodes specific geographic coordinates in Bedford County, Virginia. The coordinate digits — **371221** for latitude and **792316** for longitude — are recovered from two separate halves of the cipher, rather than as one continuous 6-digit string.

**Highlights**

- Justifies a two-digit segmentation approach as historically plausible for a 19th-century cipher.
- Uses statistical modeling (accounting for digit correlations) to show that chance alone is unlikely to produce meaningful DMS values.
- Cross-references the already-solved Cipher 2, which states that "Paper number '1' describes the exact locality of the vault."
- Concludes Cipher 1 was deliberately engineered to embed coordinate data pointing to Bedford County, Virginia.

---

## 2. Numerical Simulation of the Riemann Hypothesis

**[Read the PDF](papers/riemann-hypothesis-numerical-simulation.pdf)** · 13 pages

> Numerical simulations of the Chebyshev function ψ(x) and an approximation of the prime counting function π(x) under two scenarios: (a) all non-trivial zeros of ζ(s) lying on the critical line Re(s) = 1/2, and (b) hypothetical off-critical zeros introduced.

**Highlights**

- ψ(x) closely aligns with y = x when zeros are confined to the critical line.
- Introducing off-critical zeros produces significant deviations and irregularities in prime distribution.
- Provides computational, visual, and quantitative (MAE / RMSE) evidence supporting the necessity of RH for the regularity of primes.
- Includes the full Python source used to generate the simulations and plots (NumPy + Matplotlib).
- Intended as an educational and exploratory tool, not as a new proof.

---

## 3. AURORA-Mono (One-Piece) Rover Wheel — Build Specification

**[Read the PDF](papers/aurora-mono-wheel-build-spec.pdf)** · 4 pages

> Full build specification for AURORA-Mono, a one-piece composite rover wheel engineered for the MicroChariot interface envelope. The design combines a carbon-nanotube-reinforced PEKK structural cage with a silicon-carbide-filled PEKK wear tread, joined by a co-molded mechanical and chemical bond.

**Highlights**

- **Envelope:** 18.000 in OD × 8.000 in wide, MicroChariot-compliant hub pattern with full keep-out compliance.
- **Sandwich rim wall:** 1.20 mm skins over a 7.00 mm helical-rib core (48 ribs at ±35°, X-brace lattice).
- **Hub torque web:** 6 internal composite web-spokes (5.0 → 3.0 mm taper) with triangular lightening pockets.
- **Tread:** integral SiC-PEKK chevron lugs in two staggered rows, 75–80% void ratio, with co-molded mechanical anti-peel keys and same-family chemical bonding at 355–365 °C.
- **Mass target:** 2.21–2.30 kg as-built, with documented optimization margin down ~80–120 g.
- Includes tolerances, manufacturing sequence (additive core → autoclave skins → machining → compression-molded tread → top-coat → NDI), and a full critical-dimensions table.

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
