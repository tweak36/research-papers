# Papers

A small collection of independent research papers by **William Duckworth**.

| # | Title | Topic | Date | PDF |
|---|-------|-------|------|-----|
| 1 | Numerical Simulation of the Riemann Hypothesis: Impact of Zero Distribution on Prime Number Distribution | Number Theory / Computation | Jan 2025 | [PDF](papers/riemann-hypothesis-numerical-simulation.pdf) |
| 2 | AURORA-Mono (One-Piece) Rover Wheel — Build Specification | Mechanical / Aerospace Engineering | 2026 | [PDF](papers/aurora-mono-wheel-build-spec.pdf) |

> Other independent work lives in its own repository:
> - **Beale Cipher 1 — exploratory analysis:** [tweak36/beale-cipher-1-analysis](https://github.com/tweak36/beale-cipher-1-analysis)

---

## 1. Numerical Simulation of the Riemann Hypothesis

**[Read the PDF](papers/riemann-hypothesis-numerical-simulation.pdf)** · 13 pages

> A Python visualization of the Chebyshev function ψ(x) and an approximation of the prime counting function π(x) under two scenarios: (a) all non-trivial zeros of ζ(s) on the critical line Re(s) = 1/2, and (b) hypothetical off-critical zeros added.

**Status:** Educational simulation, not original research. The "on-critical" zeros use a uniform-spacing approximation (γₙ ≈ 14.1347 + (n−1)·20.72) rather than true Riemann zero locations, and the "off-critical" zeros are fabricated for contrast. The plots are useful for building intuition about why RH matters for the regularity of primes; they are not evidence for or against the conjecture.

**Highlights**

- Includes the full Python source used to generate the simulations and plots (NumPy + Matplotlib) — run the code and it reproduces every figure in the paper.
- Side-by-side ψ(x) and π(x) curves under both zero distributions, with MAE / RMSE reported.
- Suitable as a teaching aid or self-study companion to a chapter on analytic number theory.

---

## 2. AURORA-Mono (One-Piece) Rover Wheel

**[Read the design paper (PDF)](papers/aurora-mono-wheel-build-spec.pdf)** · 10 pages · Revision 2.0

A one-piece composite rover wheel engineered to the NASA MicroChariot interface envelope. The design pairs a carbon-nanotube-reinforced PEKK structural cage with a silicon-carbide-filled PEKK wear tread, joined through a 1.0 mm unfilled-PEKK compliant interlayer with co-molded mechanical and chemical bonding. Hub bolts are Ti-6Al-4V #10-32 UNF preloaded to 50% of proof.

![AURORA-Mono rendered overview — front view, side view, cross-section, hub pattern, wall construction, tread lug detail, and key specifications table](images/aurora-mono-overview.png)

*Rendered overview: front and side views of the wheel, through-center cross-section showing the X-brace helical lattice, plus detail callouts for the hub pattern, spoke webs, wall construction, tread lug geometry, inboard debris ports, anti-peel keys, and the full key-specifications table.*

![AURORA-Mono build specification drawing — side elevation, vertical cross-section, and materials/dimensions callouts](images/aurora-mono-build-spec.png)

*Build specification drawing AURORA-MONO-B-02: side elevation of the full wheel at 16.800 in rim OD / 18.000 in OD over lugs, vertical cross-section B-B showing the sandwich wall construction with the ±35° X-brace helical rib lattice, and materials / rim-wall / spoke / mass-target callouts.*

### Design highlights

- **Envelope:** 18.000 in OD × 8.000 in wide, MicroChariot-compliant hub pattern with full keep-out compliance.
- **Sandwich rim wall:** 1.20 mm skins over a 7.00 mm helical-rib core (48 ribs at ±35°, X-brace lattice). Total wall 10.40 mm including the 1.0 mm compliant interlayer beneath the tread.
- **Hub torque web:** 6 internal composite web-spokes (5.0 → 3.0 mm taper) with triangular lightening pockets.
- **Tread:** integral chevron lugs in two staggered rows from a reformulated ~50 vol% SiC-PEKK (α ≈ 20 ppm/K), 75–80% void ratio, chamfered lug bases for reduced edge-stress concentration, co-molded mechanical anti-peel keys, same-family chemical bonding at 355–365 °C.
- **Hub joint:** 8× Ti-6Al-4V #10-32 UNF mounting bolts + 2 jack bolts + 2 alignment pins on a Ø 4.000 in bolt circle, torqued to 50% of proof load through 12 mm pad bosses on a 6 mm composite hub adapter plate.
- **Mass target (as-built):** 2.30–2.40 kg, with ~80–120 g optimization margin identified.
- **Manufacturing flow:** additive lattice/web core → autoclave skin consolidation → machining → compliant interlayer bond → compression-molded SiC-PEKK tread → top-coat → NDI.

### Design validation

Every dimension and material choice in Revision 2.0 traces back to a quantitative validation result. The complete campaign — 13 reproducible Python screening models covering wear, structural margins, bond shear/peel, driving-load fatigue, thermal cycling, viscoelastic relaxation, the helical rib lattice, the hub bolt joint, launch loads, and modal analysis — lives in [`papers/aurora-mono-simulations/`](papers/aurora-mono-simulations/). Section 10 of the PDF summarizes the headline results in a single table; the simulations folder's README documents the method, sensitivity sweeps, and limitations of each check.

**Margins for Revision 2.0** (selected highlights):

| Failure mode | Result |
|---|---|
| Skin strip stress under impact | SF 3.14, 0 fracture flags |
| Lug shear (worst case) | SF 13 |
| Lug peel under driving loads | SF 6.1 |
| Static peel under lunar thermal cycling | SF 4.85 |
| Driving-load fatigue (Miner's rule) | D ≈ 0 (life ≫ design distance) |
| Helical rib lattice | SF >3 even worst-case load concentration |
| Hub bolt joint (yield / pad compression) | SF 2.14 / 3.33 |

### Status and scope

This is a paper design specification with closed-form Python validation — not a flight-qualified part. No 3D FEM, no fracture mechanics, no physical prototype build. Material allowables (CTE, bond strength, wear coefficient, Prony coefficients) are estimated from published PEKK / PEEK literature, not measured from production coupons. The screening campaign is the analytical envelope; the next-fidelity items (3D viscoelastic and random-vibration FEM, coupon testing, eventual prototype build at the $15K–$50K scale) are documented in Section 11 of the PDF and the simulations README. Together, the paper and the simulations folder document the complete envelope of what a closed-form Python design study can establish for a wheel of this scale.

---

## Repository layout

```
.
├── README.md
├── images/
│   ├── aurora-mono-overview.png
│   └── aurora-mono-build-spec.png
└── papers/
    ├── riemann-hypothesis-numerical-simulation.pdf
    ├── aurora-mono-wheel-build-spec.pdf
    ├── build_paper_pdf.py             (regenerates the AURORA-Mono PDF)
    └── aurora-mono-simulations/
        ├── README.md
        ├── aurora_mono_screening_model.py
        ├── aurora_mono_screening_summary.csv
        ├── aurora_mono_screening_records.csv
        ├── sensitivity_sweep.py
        ├── sensitivity_sweep_results.csv
        ├── lug_shear_check.py
        ├── lug_shear_check_results.csv
        ├── peel_check.py
        ├── peel_check_results.csv
        ├── peel_check_sensitivity.csv
        ├── fatigue_check.py
        ├── fatigue_check_summary.csv
        ├── fatigue_check_sensitivity.csv
        ├── thermal_cycle_check.py
        ├── thermal_cycle_check_summary.csv
        ├── thermal_cycle_check_sensitivity.csv
        ├── viscoelastic_relaxation_check.py
        ├── viscoelastic_relaxation_summary.csv
        ├── viscoelastic_relaxation_sensitivity.csv
        ├── rib_lattice_check.py
        ├── rib_lattice_check_summary.csv
        ├── rib_lattice_check_cases.csv
        ├── rib_lattice_check_sensitivity.csv
        ├── bolt_joint_check.py
        ├── bolt_joint_check_summary.csv
        ├── bolt_joint_check_sensitivity.csv
        ├── launch_load_check.py
        ├── launch_load_check_summary.csv
        ├── launch_load_check_sensitivity.csv
        ├── design_iteration_check.py
        ├── design_iteration_alone.csv
        ├── design_iteration_combos.csv
        ├── bolt_joint_iteration_check.py
        ├── bolt_joint_iteration_alone.csv
        ├── bolt_joint_iteration_combos.csv
        ├── modal_analysis_check.py
        ├── modal_analysis_summary.csv
        ├── modal_analysis_suspension_sensitivity.csv
        └── plots/
            ├── wear_vs_distance.png
            ├── safety_factor_running_min.png
            ├── thermal_cycle.png
            ├── sensitivity_wear.png
            ├── sensitivity_min_sf.png
            ├── fatigue_stress_histograms.png
            ├── thermal_cycle_fatigue_life.png
            ├── viscoelastic_stress_trace.png
            ├── rib_lattice_sensitivity.png
            ├── launch_load_miles.png
            ├── design_iteration_sf_vs_interlayer.png
            ├── bolt_joint_iteration.png
            └── modal_on_launch_spectrum.png
```

## Citing

If you reference either paper, please cite as:

> Duckworth, W. *Numerical Simulation of the Riemann Hypothesis: Impact of Zero Distribution on Prime Number Distribution.* 2025.

> Duckworth, W. *AURORA-Mono (One-Piece) Rover Wheel — Build Specification, Rev 1.0.* 2026.

## License

Unless otherwise stated, the papers in this repository are released under the
[Creative Commons Attribution 4.0 International License (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
