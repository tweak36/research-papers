
"""
Design iteration for the static-peel margin concern.

The thermal-cycle check (and the viscoelastic-relaxation refinement)
identified a static peel SF of 0.88 at the lug-to-skin bond on the
first cool-down to lunar night. This is the dominant identified failure
mode candidate for the AURORA-Mono design as-specified.

This script evaluates four design mitigations -- alone and in combination
-- against the goal of recovering peel SF >= 1.5:

  (A) Compliant unfilled-PEKK interlayer between tread and skin,
      with thickness as the design parameter (0.25-2.0 mm).
  (B) Reformulated SiC-PEKK with higher SiC vol fraction, dropping
      alpha_tread from 29 to 20 ppm/K.
  (C) Lower-CTE skin layup in the regions under each lug, dropping
      alpha_skin from 10 to 8 ppm/K.
  (D) Edge geometry mitigation (chamfered lug bases / scalloped
      transitions) that reduces the peel recovery factor from 0.40
      to 0.25.
  (E) Active or passive thermal management at the bond, reducing the
      effective delta_T at the bond plane from 300 K to 200 K.

Each mitigation has a multiplicative effect on the peak edge peel
stress. The script reports SF for each mitigation alone, all combined,
and identifies the minimum stack that recovers margin >= 1.5.

Model fidelity:
  Compliant interlayer effect on edge peel uses a Hart-Smith-style
  shear-lag approximation calibrated to give ~50% peel reduction at
  1.0 mm interlayer thickness (consistent with published behavior for
  thermoplastic shim layers). Real FEM with the actual interlayer
  geometry would refine this; the screening result captures the
  dominant scaling but not the precise number.

What this does NOT cover:
  - 3D FEM of the modified joint
  - Manufacturing implications of the proposed changes (e.g., adding
    an interlayer changes the molding cycle and adds process steps)
  - Mass impact (an interlayer adds ~50-100 g per wheel)
  - Effect of mitigations on driving-load checks (separate evaluation)
  - Long-term creep / fatigue of the interlayer itself
  - Bond between interlayer and adjacent layers (assumed perfect)
"""

import math
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


# ============================================================
# Baseline (matches thermal_cycle_check.py)
# ============================================================
E_TREAD_PA_BASELINE = 5.0e9
ALPHA_TREAD_BASELINE = 29.0e-6
ALPHA_SKIN_BASELINE = 10.0e-6
DELTA_T_BASELINE_K = 300.0
PEEL_RECOVERY_BASELINE = 0.40

BOND_EFFECTIVE_PEEL_MPa = 10.0
TARGET_SF = 1.5
PASS_SF = 1.5


# ============================================================
# Mitigation effects
# ============================================================
def interlayer_compliance_factor(t_interlayer_mm):
    """Edge-peel stress reduction from a compliant unfilled-PEKK
    interlayer of given thickness. Calibrated so:
      0.0 mm -> 1.00 (no reduction)
      0.5 mm -> 0.70
      1.0 mm -> 0.55
      1.5 mm -> 0.45
      2.0 mm -> 0.38

    Heuristic fit consistent with shear-lag scaling for a compliant
    PEKK shim between SiC-PEKK and PEKK-CNT/CF.
    """
    if t_interlayer_mm <= 0:
        return 1.0
    return 1.0 / (1.0 + 0.82 * t_interlayer_mm)


def constrained_peak_peel_MPa(
    E_tread_Pa, alpha_tread, alpha_skin, delta_T_K,
    peel_recovery, interlayer_factor=1.0,
):
    """Compute peak edge peel stress using the same constrained-thermal
    model as thermal_cycle_check.py, modified by the mitigation
    parameters."""
    sigma_interior = (
        E_tread_Pa * (alpha_tread - alpha_skin) * delta_T_K / 1e6
    )
    sigma_edge = sigma_interior * peel_recovery * interlayer_factor
    return sigma_edge


def evaluate_design(t_interlayer_mm=0.0,
                    alpha_tread=ALPHA_TREAD_BASELINE,
                    alpha_skin=ALPHA_SKIN_BASELINE,
                    peel_recovery=PEEL_RECOVERY_BASELINE,
                    delta_T_K=DELTA_T_BASELINE_K):
    eta = interlayer_compliance_factor(t_interlayer_mm)
    sigma = constrained_peak_peel_MPa(
        E_TREAD_PA_BASELINE, alpha_tread, alpha_skin,
        delta_T_K, peel_recovery, eta,
    )
    SF = BOND_EFFECTIVE_PEEL_MPa / sigma if sigma > 0 else float("inf")
    return {
        "t_interlayer_mm": t_interlayer_mm,
        "alpha_tread_ppm_K": alpha_tread * 1e6,
        "alpha_skin_ppm_K": alpha_skin * 1e6,
        "peel_recovery": peel_recovery,
        "delta_T_K": delta_T_K,
        "interlayer_factor": eta,
        "edge_peel_MPa": round(sigma, 3),
        "static_SF": round(SF, 3) if not math.isinf(SF) else None,
    }


# ============================================================
# Main
# ============================================================
def main():
    os.makedirs("plots", exist_ok=True)

    print("=" * 64)
    print("Design iteration: static-peel mitigation")
    print("=" * 64)
    print("Baseline design (from thermal_cycle_check.py):")
    print(f"  E_tread = {E_TREAD_PA_BASELINE/1e9:.0f} GPa, "
          f"alpha_tread = {ALPHA_TREAD_BASELINE*1e6:.1f} ppm/K, "
          f"alpha_skin = {ALPHA_SKIN_BASELINE*1e6:.1f} ppm/K")
    print(f"  delta_T = {DELTA_T_BASELINE_K:.0f} K, "
          f"peel recovery factor = {PEEL_RECOVERY_BASELINE:.2f}")
    print(f"  Bond effective allowable = {BOND_EFFECTIVE_PEEL_MPa:.1f} MPa")
    print(f"  Target SF: >= {TARGET_SF:.1f}")
    print()

    # Baseline
    baseline = evaluate_design()
    print(f"Baseline:  edge peel = {baseline['edge_peel_MPa']:.2f} MPa, "
          f"SF = {baseline['static_SF']:.2f}  (margin concern)")
    print()

    # Each mitigation alone
    print("Mitigation effects -- each alone:")
    print(f"{'Mitigation':<55}  {'edge peel':>10}  {'SF':>5}  {'>= 1.5?':>9}")
    print("-" * 84)
    mitigations_alone = [
        ("(A) +0.5 mm unfilled-PEKK interlayer",
         dict(t_interlayer_mm=0.5)),
        ("(A) +1.0 mm unfilled-PEKK interlayer",
         dict(t_interlayer_mm=1.0)),
        ("(A) +1.5 mm unfilled-PEKK interlayer",
         dict(t_interlayer_mm=1.5)),
        ("(A) +2.0 mm unfilled-PEKK interlayer",
         dict(t_interlayer_mm=2.0)),
        ("(B) Reformulated SiC-PEKK (alpha_tread 29 -> 20 ppm/K)",
         dict(alpha_tread=20e-6)),
        ("(C) Lower-CTE skin under lugs (alpha_skin 10 -> 8 ppm/K)",
         dict(alpha_skin=8e-6)),
        ("(D) Edge geometry mitigation (recovery 0.40 -> 0.25)",
         dict(peel_recovery=0.25)),
        ("(E) Thermal management (delta_T 300 -> 200 K)",
         dict(delta_T_K=200.0)),
    ]
    results_alone = []
    for label, kw in mitigations_alone:
        r = evaluate_design(**kw)
        marker = "✓" if r["static_SF"] >= PASS_SF else "✗"
        print(f"{label:<55}  {r['edge_peel_MPa']:>8.2f} MPa  "
              f"{r['static_SF']:>5.2f}  {marker:>9}")
        results_alone.append({"label": label, **r})
    print()

    # Combinations
    print("Combinations -- stacking mitigations:")
    print(f"{'Stack':<55}  {'edge peel':>10}  {'SF':>5}  {'>= 1.5?':>9}")
    print("-" * 84)
    combos = [
        ("(A,1.0mm) + (B) reformulated tread",
         dict(t_interlayer_mm=1.0, alpha_tread=20e-6)),
        ("(A,1.0mm) + (D) edge geometry",
         dict(t_interlayer_mm=1.0, peel_recovery=0.25)),
        ("(A,1.0mm) + (B) + (D)",
         dict(t_interlayer_mm=1.0, alpha_tread=20e-6, peel_recovery=0.25)),
        ("(B) + (C) + (D)",
         dict(alpha_tread=20e-6, alpha_skin=8e-6, peel_recovery=0.25)),
        ("(B) + (C) + (D) + (E)",
         dict(alpha_tread=20e-6, alpha_skin=8e-6, peel_recovery=0.25,
              delta_T_K=200.0)),
        ("All five (A=1.0mm, B, C, D, E)",
         dict(t_interlayer_mm=1.0, alpha_tread=20e-6, alpha_skin=8e-6,
              peel_recovery=0.25, delta_T_K=200.0)),
        ("All five (A=0.5mm, B, C, D, E)",
         dict(t_interlayer_mm=0.5, alpha_tread=20e-6, alpha_skin=8e-6,
              peel_recovery=0.25, delta_T_K=200.0)),
    ]
    results_combos = []
    for label, kw in combos:
        r = evaluate_design(**kw)
        marker = "✓" if r["static_SF"] >= PASS_SF else "✗"
        print(f"{label:<55}  {r['edge_peel_MPa']:>8.2f} MPa  "
              f"{r['static_SF']:>5.2f}  {marker:>9}")
        results_combos.append({"label": label, **r})
    print()

    # Search for minimum stack that recovers margin
    print("Search: minimum design changes to recover SF >= 1.5")
    print(f"{'Candidate':<55}  {'SF':>5}")
    print("-" * 64)
    min_stacks = [
        ("(A) alone -- minimum interlayer thickness", None),
        ("(A,0.25mm) + (D) edge geometry",
         dict(t_interlayer_mm=0.25, peel_recovery=0.25)),
        ("(A,0.5mm) + (D) edge geometry",
         dict(t_interlayer_mm=0.5, peel_recovery=0.25)),
        ("(B) + (D)  (no interlayer; reformulate tread + edge)",
         dict(alpha_tread=20e-6, peel_recovery=0.25)),
        ("(D) alone + (E) thermal mgmt",
         dict(peel_recovery=0.25, delta_T_K=200.0)),
    ]
    # First, find minimum interlayer thickness that works alone
    for t in np.linspace(0.1, 3.0, 30):
        r = evaluate_design(t_interlayer_mm=t)
        if r["static_SF"] >= PASS_SF:
            min_stacks[0] = (
                f"(A) alone, t_int = {t:.2f} mm",
                dict(t_interlayer_mm=t),
            )
            break
    else:
        min_stacks[0] = (
            "(A) alone -- 3.0 mm interlayer insufficient", None
        )

    for label, kw in min_stacks:
        if kw is None:
            print(f"{label:<55}  N/A")
            continue
        r = evaluate_design(**kw)
        marker = "✓" if r["static_SF"] >= PASS_SF else "✗"
        print(f"{label:<55}  {r['static_SF']:>5.2f}  {marker}")
    print()

    # ============================================================
    # CSV outputs
    # ============================================================
    df_alone = pd.DataFrame(results_alone)
    df_combos = pd.DataFrame(results_combos)
    df_alone.to_csv("design_iteration_alone.csv", index=False)
    df_combos.to_csv("design_iteration_combos.csv", index=False)
    print("Wrote design_iteration_alone.csv")
    print("Wrote design_iteration_combos.csv")
    print()

    # ============================================================
    # Plot: SF vs interlayer thickness, with and without other
    # mitigations
    # ============================================================
    fig, ax = plt.subplots(figsize=(9, 5.5))
    t_grid = np.linspace(0, 3.0, 61)
    scenarios = [
        ("Interlayer only", {}),
        ("Interlayer + edge geometry (D)",
         dict(peel_recovery=0.25)),
        ("Interlayer + reformulated tread (B)",
         dict(alpha_tread=20e-6)),
        ("Interlayer + (B) + (D)",
         dict(alpha_tread=20e-6, peel_recovery=0.25)),
    ]
    colors = ["tab:blue", "tab:orange", "tab:green", "tab:red"]
    for (label, kw), color in zip(scenarios, colors):
        SFs = []
        for t in t_grid:
            r = evaluate_design(t_interlayer_mm=t, **kw)
            SFs.append(r["static_SF"])
        ax.plot(t_grid, SFs, label=label, linewidth=2, color=color)
    ax.axhline(1.0, color="red", linestyle=":", alpha=0.7,
               label="SF = 1.0 (debond threshold)")
    ax.axhline(1.5, color="green", linestyle="--", alpha=0.7,
               label="SF = 1.5 (target margin)")
    ax.axhline(baseline["static_SF"], color="gray",
               linestyle=":", alpha=0.5,
               label=f"Baseline SF = {baseline['static_SF']:.2f}")
    ax.set_xlabel("Compliant interlayer thickness (mm)")
    ax.set_ylabel("Static peel safety factor")
    ax.set_title("AURORA-Mono — design iteration: static-peel SF "
                 "vs interlayer thickness")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(fontsize=9, loc="lower right")
    ax.set_xlim(0, 3.0)
    ax.set_ylim(0, 6.0)
    fig.tight_layout()
    fig.savefig("plots/design_iteration_sf_vs_interlayer.png", dpi=120)
    print("Wrote plots/design_iteration_sf_vs_interlayer.png")
    print()

    # ============================================================
    # Recommendation
    # ============================================================
    print("=" * 64)
    print("RECOMMENDATION")
    print("=" * 64)
    recommended = evaluate_design(
        t_interlayer_mm=1.0,
        alpha_tread=20e-6,
        peel_recovery=0.25,
    )
    print(f"Recommended design change set:")
    print(f"  (A) Add 1.0 mm unfilled-PEKK compliant interlayer between")
    print(f"      SiC-PEKK tread and PEKK-CNT/CF outer skin")
    print(f"  (B) Reformulate SiC-PEKK with higher SiC vol fraction to")
    print(f"      reduce alpha_tread from 29 to 20 ppm/K (~50 vol% SiC)")
    print(f"  (D) Add chamfered lug-base geometry to reduce edge stress")
    print(f"      concentration (peel recovery factor 0.40 -> 0.25)")
    print()
    print(f"Resulting static peel SF: {recommended['static_SF']:.2f}  "
          f"(target >= {TARGET_SF:.1f}: ✓)")
    print(f"  Edge peel stress:        "
          f"{recommended['edge_peel_MPa']:.2f} MPa")
    print(f"  Margin vs baseline:      "
          f"{recommended['static_SF']/baseline['static_SF']:.1f}x improvement")
    print()
    print("Mass / manufacturing impact (rough estimate):")
    print("  - Interlayer (A):  ~50-100 g per wheel of unfilled PEKK")
    print("  - Reformulation (B): no mass change; may increase tread")
    print("    cost from higher SiC loading and process tuning")
    print("  - Edge geometry (D): no mass change; minor tool change")
    print()
    print("This recommendation should be validated by 3D viscoelastic FEM")
    print("with the proposed interlayer in place, coupon-test peel data")
    print("for the SiC-PEKK / unfilled-PEKK / PEKK-CNT/CF stack, and")
    print("re-running the bond-shear and lug-peel screening checks with")
    print("the new layer in place.")
    print()
    print("Single-change alternatives that also meet SF >= 1.5:")
    for label, kw in min_stacks[1:]:
        r = evaluate_design(**kw)
        if r["static_SF"] >= PASS_SF:
            print(f"  - {label}: SF = {r['static_SF']:.2f}")


if __name__ == "__main__":
    main()
