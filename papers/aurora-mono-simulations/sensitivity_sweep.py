
"""
One-at-a-time sensitivity sweep on the four dominant screening parameters.

For each parameter, run the screening model at five levels (-50%, -25%,
nominal, +25%, +50%) and report:
- final cumulative wear (mm)
- minimum safety factor (skin strip stress)
- minimum traction margin (mu)
- fracture flags (segments with SF < 1)

Outputs:
- sensitivity_sweep_results.csv  (one row per (parameter, level))
- plots/sensitivity_wear.png     (wear vs % change for each parameter)
- plots/sensitivity_min_sf.png   (min SF vs % change for each parameter)

Limitations:
- One-at-a-time only; does not capture interaction effects.
- Each run uses seed=7, so stochastic realizations are correlated across
  runs (the same sequence of rock/side events occurs each time, scaled by
  parameter changes). This is intentional for cleaner trend extraction.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

from aurora_mono_screening_model import run_screening, DEFAULT_PARAMS

LEVELS = [-0.50, -0.25, 0.00, 0.25, 0.50]

PARAMS_TO_SWEEP = [
    ("wear_k_cold", "cold-temp wear coefficient"),
    ("instant_contact_fraction", "instant contact fraction"),
    ("payload_mass_kg", "payload mass (kg)"),
    ("dynamic_spike_factor", "dynamic load spike factor"),
]


def main():
    os.makedirs("plots", exist_ok=True)
    results = []
    for param, label in PARAMS_TO_SWEEP:
        baseline = DEFAULT_PARAMS[param]
        print(f"\n=== Sweeping {param} (baseline {baseline}) ===")
        for level in LEVELS:
            value = baseline * (1 + level)
            _, summary = run_screening(**{param: value})
            row = {
                "parameter": param,
                "label": label,
                "level_pct": int(level * 100),
                "value": value,
                "final_wear_mm": round(summary["final_wear_mm"], 4),
                "min_safety_factor": round(summary["minimum_safety_factor"], 4),
                "min_traction_margin": round(
                    summary["minimum_traction_margin_mu"], 4
                ),
                "fracture_flags": int(summary["fracture_flags_SF_lt_1"]),
                "max_load_N": round(summary["max_load_N_seen"], 2),
            }
            results.append(row)
            print(
                f"  {level:+.0%}  value={value:<10.4g}"
                f"  wear={row['final_wear_mm']:>7.3f} mm"
                f"  minSF={row['min_safety_factor']:>5.2f}"
                f"  fractures={row['fracture_flags']}"
            )

    df = pd.DataFrame(results)
    df.to_csv("sensitivity_sweep_results.csv", index=False)
    print("\nWrote sensitivity_sweep_results.csv")

    # Plot 1: wear vs % change
    fig, ax = plt.subplots(figsize=(8, 5))
    for param, label in PARAMS_TO_SWEEP:
        sub = df[df["parameter"] == param]
        ax.plot(sub["level_pct"], sub["final_wear_mm"], marker="o", label=label)
    ax.set_xlabel("Parameter change from nominal (%)")
    ax.set_ylabel("Final cumulative wear (mm) over 1000 km")
    ax.set_title("AURORA-Mono — wear sensitivity (one-at-a-time)")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.axhline(9.0, color="black", linestyle=":", alpha=0.5, label="nominal lug height")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig("plots/sensitivity_wear.png", dpi=120)
    print("Wrote plots/sensitivity_wear.png")

    # Plot 2: min safety factor vs % change
    fig, ax = plt.subplots(figsize=(8, 5))
    for param, label in PARAMS_TO_SWEEP:
        sub = df[df["parameter"] == param]
        ax.plot(sub["level_pct"], sub["min_safety_factor"], marker="o", label=label)
    ax.set_xlabel("Parameter change from nominal (%)")
    ax.set_ylabel("Minimum safety factor (skin strip stress)")
    ax.set_title("AURORA-Mono — min safety factor sensitivity")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.axhline(1.0, color="red", linestyle=":", alpha=0.7, label="SF = 1 (failure)")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig("plots/sensitivity_min_sf.png", dpi=120)
    print("Wrote plots/sensitivity_min_sf.png")


if __name__ == "__main__":
    main()
