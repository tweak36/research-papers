# Papers

A small collection of independent research papers by **William Duckworth**.

| # | Title | Topic | Date | PDF |
|---|-------|-------|------|-----|
| 1 | Deciphering Beale Cipher 1: A Comprehensive Statistical and Geographical Analysis | Cryptography / History | Feb 2025 | [PDF](papers/deciphering-beale-cipher-1.pdf) |
| 2 | Numerical Simulation of the Riemann Hypothesis: Impact of Zero Distribution on Prime Number Distribution | Number Theory / Computation | Jan 2025 | [PDF](papers/riemann-hypothesis-numerical-simulation.pdf) |

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

## Repository layout

```
.
├── README.md
└── papers/
    ├── deciphering-beale-cipher-1.pdf
    └── riemann-hypothesis-numerical-simulation.pdf
```

## Citing

If you reference either paper, please cite as:

> Duckworth, W. *Deciphering Beale Cipher 1: A Comprehensive Statistical and Geographical Analysis.* 2025.

> Duckworth, W. *Numerical Simulation of the Riemann Hypothesis: Impact of Zero Distribution on Prime Number Distribution.* 2025.

## License

Unless otherwise stated, the papers in this repository are released under the
[Creative Commons Attribution 4.0 International License (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
