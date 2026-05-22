# AURORA-Mono — First-Order Screening Analysis

A reproducible Python screening model that estimates wear, structural safety factor, and traction margin for the [AURORA-Mono](../aurora-mono-wheel-build-spec.pdf) one-piece rover wheel over 1000 km of lunar driving.

## Status — read this first

**This is a *screening* analysis, not a qualification analysis.**

- Not FEA. The structural check is a single local strip-stress calculation against an allowable; the helical X-brace lattice is not analyzed.
- Not a true thermal simulation. Temperature is a prescribed schedule that only modulates the wear coefficient; no radiation balance, no conduction through the wall, no regolith heat transfer.
- Not fracture mechanics. No crack growth, no fatigue accumulator, no spallation prediction.
- Wear coefficients are estimated, not measured from SiC-PEKK coupon tests.
- Regolith abrasivity is represented indirectly through a cold-biased wear coefficient.
- No prototype has been built or physically tested.

The purpose is **design-direction screening**: confirm the wheel is in the right ballpark before committing to a detailed simulation or test campaign, and surface the assumptions that would dominate the answer at next fidelity.

## What the model computes

For 50,000 segments of 20 m each (1000 km total):

| Quantity | How it's computed |
|---|---|
| Per-segment temperature | Prescribed schedule cycling through −170, −100, −40, 0, +60 °C with dwell hours weighted to a Moon-like duty |
| Per-segment wear depth | Archard-style: `k(T) · F · L_slide / H_tread`, distributed over a contact area `2πR·W · 0.20 · 0.20` |
| Wear coefficient `k(T)` | Linear interpolation between 1.8e-4 (warm) and 3.8e-4 (cold) |
| Terrain | Stochastic categorical (60% loose / 30% compact / 10% rocky) with terrain-specific available μ |
| Rock impact events | 5% per segment, with rock-size fractions sampled from a heavy-tailed distribution; load spike up to 4× static |
| Side impacts | 2% per segment; load × 1.2 |
| Local stress | `F / (10 mm × 1.2 mm)` — a single strip across the outer skin |
| Safety factor | `σ_allow / σ_local`, with 160 MPa allowable for the PEKK-CNT/CF skin |
| Traction margin | `μ_available − μ_required(20°)` |

## Headline results

From `aurora_mono_screening_summary.csv`:

| Metric | Value |
|---|---|
| Distance simulated | 1000 km |
| Static load per wheel | 127.6 N (Moon gravity, 45 kg rover + 270 kg payload, 4 wheels) |
| Max load seen (rock event) | 612 N |
| Rock events | 2,429 / 50,000 segments |
| Side impacts | 961 / 50,000 segments |
| **Final cumulative wear** | **9.0 mm** (of 9.0 mm nominal lug height — i.e. lugs fully worn at end of life) |
| **Minimum safety factor** | **3.14** (on the local strip-stress check) |
| Fracture flags (SF < 1) | 0 |
| Median traction margin | μ = +0.186 (well above the 0.364 required for a 20° slope) |
| Minimum traction margin | μ = +0.036 (just above zero on a 20° slope in the worst sampled segment) |

### Plots

| | |
|---|---|
| ![Cumulative wear vs distance](plots/wear_vs_distance.png) | ![Running minimum safety factor](plots/safety_factor_running_min.png) |
| Cumulative wear vs distance | Running minimum safety factor |

![Prescribed thermal cycle](plots/thermal_cycle.png)
*Prescribed wheel-temperature schedule used to modulate the wear coefficient.*

## How to reproduce

Requires Python 3.x with NumPy and pandas.

```bash
pip install numpy pandas matplotlib
python aurora_mono_screening_model.py
```

The script is deterministic (`np.random.seed(7)`) — anyone running it will reproduce the same per-segment records and summary numbers.

Outputs written to the current directory:

- `aurora_mono_screening_records.csv` — 50,000-row per-segment log (temperature, terrain, speed, load, stress, safety factor, cumulative wear, traction margin)
- `aurora_mono_screening_summary.csv` — 1-row mission summary

## Companion analyses

Two follow-on scripts run on top of the same screening model:

### Sensitivity sweep — [`sensitivity_sweep.py`](sensitivity_sweep.py)

One-at-a-time sensitivity on the four dominant parameters, ±50% and ±25%:

| Parameter | Effect on wear | Effect on min SF |
|---|---|---|
| `wear_k_cold` | linear: 5.3 → 12.8 mm | none (no load coupling) |
| `instant_contact_fraction` | **inverse, dominant: 18.0 → 6.0 mm** | none |
| `payload_mass_kg` | linear: 5.1 → 12.9 mm | 5.5 → 2.2 |
| `dynamic_spike_factor` | small: 8.5 → 9.5 mm | 6.3 → 2.1 |

**Key finding:** at the worst-case end of the contact-fraction assumption (−50%, i.e. only 2% of the wheel surface in contact at any instant), cumulative wear reaches **18 mm — exceeding the 9 mm nominal lug height**. That single assumption dominates the wear answer and is the highest-priority parameter to nail down with measurement.

**Robustness on stress:** the minimum safety factor stays above 2 across all ±50% perturbations, with zero fracture flags in every run.

| | |
|---|---|
| ![Wear sensitivity](plots/sensitivity_wear.png) | ![Min SF sensitivity](plots/sensitivity_min_sf.png) |
| Final wear vs ± parameter change | Min safety factor vs ± parameter change |

Outputs: [`sensitivity_sweep_results.csv`](sensitivity_sweep_results.csv).

### Lug-shear check — [`lug_shear_check.py`](lug_shear_check.py)

Screening check on the SiC-PEKK tread / PEKK-CNT/CF outer-skin co-molded bond. Uses the mission's peak normal load (612 N from the worst rock event in the stochastic history), the maximum terrain traction coefficient (μ = 0.55, loose terrain), and distributes the resulting tangential force across the estimated 2 lugs in instantaneous contact. Applies a 2.5× edge-stress concentration factor.

| Case | Shear stress (design) | Safety factor |
|---|---|---|
| Nominal (2 lugs in contact) | 0.75 MPa | **26.6** |
| Worst plausible (1 lug bearing all load) | 1.50 MPa | **13.3** |

Allowable shear is set at 20 MPa, derived conservatively as 40% of the low end of PEKK bulk shear strength (50 MPa). Anti-peel mechanical interlock from the keying grooves is **not** credited.

**Verdict:** the lug-to-skin bond is not the limiting failure mode in pure shear. Peel-mode loading is analyzed separately in `peel_check.py` below.

Outputs: [`lug_shear_check_results.csv`](lug_shear_check_results.csv).

### Peel check — [`peel_check.py`](peel_check.py)

The mode the anti-peel keys are specifically designed for. When the wheel crests a rock, the contact patch shifts to one edge of a lug, putting that lug under a bending moment that wants to lift its trailing edge.

The model treats each lug as a rigid rectangular pad bonded to the skin and applies the per-lug normal load at a horizontal offset `e` from the centerline. The peak peel stress at the trailing edge follows from beam bending: `σ_peak = 6·M / (b·L²)`. This is compared against an effective allowable that combines the chemical bond strength (5 MPa, conservative for thermoplastic same-family co-mold) with a multiplier crediting the mechanical anti-peel keys (2.0× nominal).

**Nominal cases** (chemical 5 MPa × 2.0× key multiplier = 10 MPa effective):

| Case | Peak peel stress | Safety factor |
|---|---|---|
| Cruise, centered load (e = 0) | 0 MPa | ∞ |
| Cruise, moderate eccentricity (e = L/4) | 0.17 MPa | 58.5 |
| Cruise, worst eccentricity (e = L/2) | 0.34 MPa | 29.3 |
| Worst rock event, moderate eccentricity | 0.82 MPa | 12.2 |
| **Worst rock event, worst eccentricity (e = L/2)** | **1.64 MPa** | **6.1** |

**Sensitivity** on the two most uncertain inputs (chemical allowable and key multiplier), at the worst-case load and offset:

| Chemical allowable | Key multiplier | Effective allowable | SF (worst case) |
|---|---|---|---|
| 3 MPa | 1.0× (no key credit) | 3 MPa | 1.8 |
| 5 MPa | 1.0× | 5 MPa | 3.0 |
| 5 MPa | 2.0× (nominal) | 10 MPa | **6.1** |
| 10 MPa | 2.0× | 20 MPa | 12.2 |
| 15 MPa | 3.0× (optimistic) | 45 MPa | 27.4 |

**Verdict:** adequate peel margin under nominal assumptions. The worst case in the entire sensitivity grid (no key credit + lowest plausible chemical allowable) still gives SF 1.8 — marginal but positive. Most realistic combinations yield SF 3–12.

**This is a stress-based screening check, not fracture mechanics.** The correct next-fidelity step is a G_c-based crack-propagation analysis using a measured critical strain energy release rate for the actual co-mold bond.

Outputs: [`peel_check_results.csv`](peel_check_results.csv) (the 5 named cases) and [`peel_check_sensitivity.csv`](peel_check_sensitivity.csv) (the 15-row grid).

### Fatigue check — [`fatigue_check.py`](fatigue_check.py)

Miner's-rule fatigue damage accumulator on both the rim skin and the lug-skin bond peel. For each segment in the mission, the screening model's recorded stress is used to compute damage per Miner's rule (`D = Σ n_i / N_f(σ_i)`); failure at `D = 1.0`, fatigue safety factor is `1/D`. Wheel circumference and segment length give ~14 stress cycles per segment, ~696,000 cycles total over 1000 km.

S-N curves use a Basquin-style log-linear fit calibrated to `N_f = 1` at the static strength and `N_f = 10⁶` at a representative endurance limit. Stresses below the endurance limit accumulate zero damage (infinite-life assumption).

| Component | σ_static | Endurance ratio R_e | Endurance limit | Stress range observed | Cycles above endurance | Total damage D | Fatigue SF | Implied life |
|---|---|---|---|---|---|---|---|---|
| Skin (PEKK-CNT/CF) | 160 MPa | 0.40 | 64 MPa | 10.6 – 51.0 MPa | **0** | 0 | ∞ | ∞ |
| Bond peel (nominal, with keys) | 10 MPa | 0.25 | 2.5 MPa | 0.17 – 1.64 MPa | **0** | 0 | ∞ | ∞ |

Every cycle, on both components, falls below the endurance limit. Visually:

![Fatigue stress histograms](plots/fatigue_stress_histograms.png)

**Sensitivity** on the bond, sweeping chemical allowable (3, 5, 7 MPa), key multiplier (1, 2, 3×), and endurance ratio (0.20, 0.25, 0.30) — 27 combinations:

| Combination | Fatigue life |
|---|---|
| Most adverse (3 MPa chem × no key credit × R_e = 0.20) | ~7,200 km |
| Adverse (3 MPa chem × no key credit × R_e = 0.25) | ~14,600 km |
| 5 MPa chem × no key credit × R_e = 0.20 | ~161,000 km |
| Nominal (5 MPa chem × 2× key × R_e = 0.25) | infinite |
| Most combinations with key credit | infinite |

**Verdict:** the design has enough static margin that fatigue is not the governing failure mode under the modeled load spectrum. Even the most adverse parameter combinations show fatigue life > 7× the 1000 km design distance.

**Caveats this check does NOT capture:**
- Mean-stress effects (Goodman / Soderberg corrections).
- Load-sequence interaction.
- Crack-growth-based life prediction (Paris law on G_c).
- Thermal-cycling stress from differential CTE — analyzed separately in `thermal_cycle_check.py` below.

Outputs: [`fatigue_check_summary.csv`](fatigue_check_summary.csv) and [`fatigue_check_sensitivity.csv`](fatigue_check_sensitivity.csv).

### Thermal-cycling check — [`thermal_cycle_check.py`](thermal_cycle_check.py)

> **This is the first screening check to surface a real margin concern. Read this section carefully.**

When the wheel sits on the lunar surface, the bonded interface between the SiC-PEKK tread and the PEKK-CNT/CF outer skin sees cyclic stress from differential thermal expansion. The lunar diurnal swing is ΔT ≈ 300 K (−173 to +127 °C) over a 29.5-day cycle, giving ~12.4 thermal cycles per Earth year.

The constrained-strain upper bound on interfacial stress is `σ = E_tread · Δα · ΔT`. Real peak peel at lug edges is some fraction of this bound; the model sweeps a "peel recovery factor" from 0.3 (heavily relaxed) to 1.0 (no relaxation).

**Material assumptions** (estimated, not measured):

| Material | E | α (CTE) |
|---|---|---|
| Tread SiC-PEKK | 5 GPa | 29 ppm/K |
| Skin PEKK-CNT/CF (in-plane) | 50 GPa | 10 ppm/K |
| **Δα** | | **19 ppm/K** |

**Nominal result** (Δα = 19 ppm/K, edge recovery factor = 0.40, ΔT = 300 K):

| Quantity | Value |
|---|---|
| Interior constrained shear (full cycle) | 28.5 MPa |
| Estimated peak peel at lug edge | 11.4 MPa |
| Bond effective allowable | 10.0 MPa |
| **Static SF on edge peel** | **0.88** |
| Stress vs bond endurance limit (2.5 MPa) | 11.4 MPa ≫ 2.5 MPa → cycles count toward fatigue |
| Cycles to failure | ~0.5 |
| **Implied bond fatigue life** | **~15 days (less than one lunar day)** |

**Sensitivity** on the two most uncertain inputs:

![Thermal-cycle bond fatigue life vs Δα](plots/thermal_cycle_fatigue_life.png)

| Δα (ppm/K) | Recovery factor | Edge peel | Static SF | Fatigue life |
|---|---|---|---|---|
| 10 | 0.30 | 4.5 MPa | 2.22 | ~2,000 years |
| 10 | 0.40 | 6.0 MPa | 1.67 | ~130 years |
| 15 | 0.30 | 6.75 MPa | 1.48 | ~32 years |
| 15 | 0.40 | 9.0 MPa | 1.11 | ~186 days |
| **19** (nominal) | **0.40** (nominal) | **11.4 MPa** | **0.88** | **~15 days** |
| 19 | 0.30 | 8.55 MPa | 1.17 | ~1.2 years |
| 25 | any | ≥11.25 MPa | ≤0.89 | ≤15 days |
| 30 | any | ≥13.5 MPa | ≤0.74 | ≤15 days |

**Honest verdict**

Under the nominal estimated material properties, **thermal cycling alone is the dominant failure mode candidate**. The constrained-strain peak peel stress (~11 MPa) is slightly above the bond's static allowable (~10 MPa), and well above its endurance limit (2.5 MPa). The driving-load checks (strip stress, lug shear, lug peel, driving-cycle fatigue) all showed comfortable margins; this passive thermal check is the one that doesn't.

**The numerical result is highly sensitive to assumptions.** The constrained-strain model is intentionally conservative — it does NOT credit:
- Viscoelastic / creep relaxation in PEKK during long lunar-day dwells at +127 °C (Tg ≈ 165 °C is uncomfortably close — meaningful creep is expected).
- Through-thickness compliance of the sandwich wall.
- Any compliant interlayer between SiC-PEKK and PEKK-CNT/CF.
- Edge geometry detail (chamfers, fillets) that distributes the singularity.

The result *should* be read as: **this is the failure mode to instrument and design against**, not "the design fails." A real evaluation needs viscoelastic FEA with measured material properties.

**Mitigations to consider in any next design iteration:**

- Compliant interlayer (e.g. unfilled PEKK strip) between tread and skin to absorb CTE mismatch.
- Reformulate SiC-PEKK with higher SiC vol-fraction to drop α_tread.
- Lower-modulus / lower-CTE skin layup in the regions under each lug.
- Edge geometry (chamfered lug bases, scalloped transitions) to spread the strain singularity.
- Active or passive thermal management at the bond.

**Next-fidelity step:** viscoelastic FEM (Prony-series PEKK material model) with measured CTE values for both formulations, run over the full diurnal cycle.

Outputs: [`thermal_cycle_check_summary.csv`](thermal_cycle_check_summary.csv) and [`thermal_cycle_check_sensitivity.csv`](thermal_cycle_check_sensitivity.csv).

## Files in this folder

```
aurora-mono-simulations/
├── README.md                              (this file)
├── aurora_mono_screening_model.py         (refactored model + run_screening() API)
├── aurora_mono_screening_summary.csv      (1-row mission summary)
├── aurora_mono_screening_records.csv      (50k-row per-segment log)
├── sensitivity_sweep.py                   (±50/25% sweep on 4 params)
├── sensitivity_sweep_results.csv          (20-row sweep result table)
├── lug_shear_check.py                     (bond-shear screening check)
├── lug_shear_check_results.csv            (lug-shear screening result)
├── peel_check.py                          (bond-peel screening check)
├── peel_check_results.csv                 (5 peel load/eccentricity cases)
├── peel_check_sensitivity.csv             (15-row sensitivity grid)
├── fatigue_check.py                       (Miner's-rule fatigue accumulator)
├── fatigue_check_summary.csv              (skin + bond fatigue summary)
├── fatigue_check_sensitivity.csv          (27-row bond fatigue sensitivity)
├── thermal_cycle_check.py                 (CTE-mismatch thermal cycling)
├── thermal_cycle_check_summary.csv        (single-cycle + fatigue summary)
├── thermal_cycle_check_sensitivity.csv    (25-row Δα × recovery sweep)
└── plots/
    ├── wear_vs_distance.png
    ├── safety_factor_running_min.png
    ├── thermal_cycle.png
    ├── sensitivity_wear.png
    ├── sensitivity_min_sf.png
    ├── fatigue_stress_histograms.png
    └── thermal_cycle_fatigue_life.png
```

## Sensitivity & assumptions to bear in mind

The two parameters that dominate the wear answer are both estimated, not measured:

| Parameter | Value used | Effect of ±50% change |
|---|---|---|
| `k_cold` (cold-temperature wear coefficient) | 3.8 × 10⁻⁴ | Final wear scales roughly linearly → 4.5 mm or 13.5 mm |
| `lug_coverage × instant_contact_fraction` | 0.20 × 0.20 = 0.04 of total surface | Final wear scales inversely → could double or halve |

A formal sensitivity sweep is not yet included.

## Open work — what would strengthen this at next fidelity

In rough order of impact:

1. ~~Sensitivity sweep~~ — **added** (see `sensitivity_sweep.py`). Identified `instant_contact_fraction` as the dominant-but-uncertain wear parameter.
2. ~~Lug-shear check~~ — **added** (see `lug_shear_check.py`). SF 13–27 in shear.
3. ~~Peel-mode bond check~~ — **added** (see `peel_check.py`). SF 6.1 nominal under driving loads.
4. ~~Miner's-rule fatigue accumulator~~ — **added** (see `fatigue_check.py`). Driving-load fatigue not a concern.
5. ~~Thermal-cycling stress from differential CTE~~ — **added** (see `thermal_cycle_check.py`). **Surfaced as the dominant failure-mode candidate.** Result is highly sensitive to assumptions; next-fidelity work below is now urgent rather than merely thorough.
6. **Viscoelastic FEM with Prony-series PEKK** under the diurnal cycle, with measured CTE / modulus values for the actual SiC-PEKK and PEKK-CNT/CF formulations. This is the most important single next step — it converts the current screening "margin concern" into either a real concern or a non-issue.
7. **Coupon-test CTE values** for the two formulations (the screening uses rule-of-mixtures estimates).
8. **Fracture-mechanics peel analysis** using G_c (Paris-law crack growth) for the actual co-mold bond.
9. **Helical X-brace rib analysis** — the lattice is the wheel's structural load path and is not currently modeled.
10. **Real thermal model** — radiation balance, 1D conduction through the sandwich wall, regolith contact, sun/shadow cycling.
11. **Coupon-test wear coefficients** for SiC-PEKK against JSC-1A lunar regolith simulant, replacing the estimated `k(T)`.
12. **Coupon-test bond strength** (shear, peel, G_c, S-N) for the co-molded PEKK joint, replacing the estimated allowables in the screening scripts.
13. **Design iteration:** evaluate a compliant interlayer (unfilled PEKK), reformulated SiC-PEKK, or edge geometry mitigations targeting the thermal-cycle failure mode identified in (5).

## License

CC0 / public domain for the code. CC BY 4.0 for the writeup and plots, consistent with the rest of the repository.
