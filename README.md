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

## 2. AURORA-Mono (One-Piece) Rover Wheel — Build Specification

**[Read the PDF](papers/aurora-mono-wheel-build-spec.pdf)** · 4 pages

![AURORA-Mono rendered overview — front view, side view, cross-section, hub pattern, wall construction, tread lug detail, and key specifications table](images/aurora-mono-overview.png)

*Rendered overview: front and side views of the wheel, through-center cross-section showing the X-brace helical lattice, plus detail callouts for the hub pattern, spoke webs, wall construction, tread lug geometry, inboard debris ports, anti-peel keys, and the full key-specifications table.*

![AURORA-Mono build specification drawing — side elevation, vertical cross-section, and materials/dimensions callouts](images/aurora-mono-build-spec.png)

*Build specification drawing AURORA-MONO-B-01 (Rev 2026-02-15): side elevation of the full wheel at 16.800 in rim OD / 18.000 in OD over lugs, vertical cross-section B-B showing the sandwich wall construction with the ±35° X-brace helical rib lattice, and materials / rim-wall / spoke / mass-target callouts.*

> A paper design study for a one-piece composite rover wheel engineered to the MicroChariot interface envelope. The design pairs a carbon-nanotube-reinforced PEKK structural cage with a silicon-carbide-filled PEKK wear tread, joined by a co-molded mechanical and chemical bond.

**Status:** Paper design plus a coordinated set of first-order Python screening analyses (see [`papers/aurora-mono-simulations/`](papers/aurora-mono-simulations/)). No FEA, no fracture mechanics, no physical prototype. Material allowables and contact assumptions are estimated, not derived from coupon tests. Intended for design-direction screening, not qualification.

**Highlights**

- **Envelope:** 18.000 in OD × 8.000 in wide, MicroChariot-compliant hub pattern with full keep-out compliance.
- **Sandwich rim wall:** 1.20 mm skins over a 7.00 mm helical-rib core (48 ribs at ±35°, X-brace lattice).
- **Hub torque web:** 6 internal composite web-spokes (5.0 → 3.0 mm taper) with triangular lightening pockets.
- **Tread:** integral SiC-PEKK chevron lugs in two staggered rows, 75–80% void ratio, with co-molded mechanical anti-peel keys and same-family chemical bonding at 355–365 °C.
- **Mass target (design intent):** 2.21–2.30 kg, with ~80–120 g optimization margin identified.
- Includes tolerances, a proposed manufacturing sequence (additive core → autoclave skins → machining → compression-molded tread → top-coat → NDI), and a full critical-dimensions table.

### Screening analyses

Twelve reproducible Python screening models live in [`papers/aurora-mono-simulations/`](papers/aurora-mono-simulations/). Each has its own script, CSV outputs, and (where applicable) plots. The simulations README documents what every check does, doesn't, and means.

| Check | Mode | Headline result |
|---|---|---|
| Strip stress (main screening model) | Skin tensile under impact | Min SF 3.14, 0 fracture flags |
| Sensitivity sweep | Robustness of wear and SF to dominant parameters | Min SF >2.1 across ±50%; wear sensitive to contact-fraction assumption |
| Lug shear | SiC-PEKK / skin bond in shear | SF 13–27 |
| Lug peel (driving loads) | SiC-PEKK / skin bond peel from eccentric load | SF 6.1 nominal, ≥1.8 across full sensitivity |
| Miner's-rule fatigue (driving cycles) | Skin and bond fatigue over ~696,000 wheel rotations | D ≈ 0; life >7,200 km in worst sensitivity |
| Thermal cycling (CTE mismatch) | Static peel from lunar diurnal swing | **Static SF 0.88 — baseline sub-unity result** |
| Viscoelastic relaxation (Prony + TTS, *not* FEM) | Refines the thermal check | Fatigue life ~247 years; static SF stays 0.88–0.92; failure mode is static debond on first cool-down |
| Helical rib lattice | Per-rib stress, buckling, effective core shear | Yield/buckling SF >3 even with one rib bearing the full rock-event load; SF ~280 under uniform sharing |
| Hub bolt joint | Preloaded bolts, shear, bearing, pad-boss compression | **Yield SF 1.38, pad-boss compression SF 1.82 — baseline marginal-but-positive** |
| Launch load (QS + Miles random vib) | Hub joint under 6g QS + random-vib equivalent | Launch loads do not govern — operational driving loads are larger per bolt; first-mode estimate of ~15 Hz is the one flag |
| Design iteration on static peel | Mitigations against SF 0.88 baseline | Recommended stack (1.0 mm interlayer + reformulated tread + edge geometry) recovers **SF 4.85**, a 5.5× improvement |
| Design iteration on bolt joint | Mitigations against SF 1.38 / 1.82 baseline | Recommended stack (Ti-6Al-4V bolts at 50% preload) recovers **yield SF 2.14, pad SF 3.33** |

**Honest combined verdict.** Of twelve checks, both originally identified margin concerns — the static peel debond (SF 0.88) and the hub bolt joint margins (SF 1.38 / 1.82) — are now resolved on paper by specific design changes from the two iteration scripts. The full recommended set: **(1) 1.0 mm unfilled-PEKK compliant interlayer between tread and skin, (2) reformulated SiC-PEKK with α_tread reduced to 20 ppm/K, (3) chamfered lug-base edge geometry, (4) Ti-6Al-4V hub bolts at 50% proof preload.** With these changes the wheel meets SF ≥ 2.0 on all checked failure modes and SF ≥ 1.5 on the static-peel mode. Launch loads don't govern any check at the wheel's 2.3 kg mass. The remaining open work is validation: 3D viscoelastic FEM with measured Prony coefficients, modal analysis with the rover suspension, coupon tests for all estimated material properties, and physical prototype build and test.

**Open work before this would be a real engineering artifact:** validation of the recommended design stacks (static-peel and bolt-joint) via 3D viscoelastic FEM + coupon tests; 3D truss/solid FEM of the rib lattice with realistic contact-patch pressure distribution; bolt-joint creep + fatigue under lunar thermal cycling (the iteration check is initial-condition only); modal analysis with rover-suspension boundary conditions; lattice and skin response to distributed inertial body loads under launch; coupon-test material properties (CTE, bond shear / peel / G_c / S-N, wear coefficient); a real thermal model (radiation balance + 1D conduction); fracture-mechanics peel analysis using measured G_c; physical prototype build and test.

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
            └── bolt_joint_iteration.png
```

## Citing

If you reference either paper, please cite as:

> Duckworth, W. *Numerical Simulation of the Riemann Hypothesis: Impact of Zero Distribution on Prime Number Distribution.* 2025.

> Duckworth, W. *AURORA-Mono (One-Piece) Rover Wheel — Build Specification, Rev 1.0.* 2026.

## License

Unless otherwise stated, the papers in this repository are released under the
[Creative Commons Attribution 4.0 International License (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
