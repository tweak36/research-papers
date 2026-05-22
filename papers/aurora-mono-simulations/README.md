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

## Files in this folder

```
aurora-mono-simulations/
├── README.md                              (this file)
├── aurora_mono_screening_model.py         (the model, ~140 lines)
├── aurora_mono_screening_summary.csv      (1-row mission summary)
├── aurora_mono_screening_records.csv      (50k-row per-segment log)
└── plots/
    ├── wear_vs_distance.png
    ├── safety_factor_running_min.png
    └── thermal_cycle.png
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

1. **Sensitivity sweep** over `k`, contact area, and load assumptions — would convert single-point numbers into defensible ranges.
2. **Lug-shear check at the SiC-PEKK / outer-skin keying interface** — likely the more critical failure mode than skin strip stress.
3. **Miner's-rule fatigue accumulator** on the skin under cyclic loading — instantaneous SF > 1 is not the same as 1000 km of cyclic loading being safe.
4. **Helical X-brace rib analysis** — the lattice is the wheel's structural load path and is not currently modeled.
5. **Real thermal model** — radiation balance, 1D conduction through the sandwich wall, regolith contact, sun/shadow cycling.
6. **Coupon-test wear coefficients** for SiC-PEKK against JSC-1A lunar regolith simulant, replacing the estimated `k(T)`.

## License

CC0 / public domain for the code. CC BY 4.0 for the writeup and plots, consistent with the rest of the repository.
