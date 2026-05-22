
"""
Design iteration for the hub bolt joint margins.

The bolt-joint check found two marginal-but-positive SFs at the nominal
design (A286 stainless, 70% proof preload, 12 mm pad bosses):

  Bolt yield SF        = 1.38
  Pad-boss compression = 1.82

This script evaluates five design changes against the goal of recovering
both SFs to >= 2.0 (the typical aerospace screening target):

  (P) Reduce preload factor: 70% -> 50% of proof
  (D) Increase pad-boss diameter: 12 mm -> 14, 16, 18 mm
  (M) Change bolt material: A286 stainless -> Ti-6Al-4V
  (S) Upsize bolt: #10-32 UNF -> #1/4-28 UNF (more invasive)
  (N) More bolts: 8 -> 10 or 12 (most invasive)

Each change has known mechanics:

  Yield SF is preload-dominated. Lower preload factor or lower-tensile
  material (lower preload at the same %) directly improves yield SF.
  Bolt size and bolt count barely affect it because preload stress is
  set by preload factor, not by absolute force.

  Pad compression SF scales as A_pad / preload, so larger pad bosses
  or lower preload directly improve it. Larger bolts INCREASE preload
  proportionally (worsening pad SF unless compensated by larger pad).

Target: both SFs >= 2.0.

What this does NOT cover:
  - Reduced separation margin from lower preload (still checked but not
    re-targeted; baseline sep SF = 39 has substantial headroom)
  - Effect of design changes on joint stiffness or vibration behaviour
  - Bolt fatigue under cyclic mission loads
  - Pad-boss creep under sustained preload at +127 C (a separate
    open-work item)
  - Mass / cost impact of design changes (rough notes only)
"""

import math
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from bolt_joint_check import (
    BOLT_MATERIALS,
    JOINT_STIFFNESS_RATIO_C,
    PROOF_FACTOR,
    COMPOSITE_COMPRESSION_ALLOWABLE_MPa,
    BOLT_CIRCLE_RADIUS_M,
    AXIAL_OFFSET_M,
    WHEEL_RADIUS_M,
    MU_MAX,
    LATERAL_FRACTION,
)
from aurora_mono_screening_model import run_screening


# ============================================================
# Bolt size options (#10-32 baseline, #1/4-28 upsized)
# ============================================================
IN = 0.0254
BOLT_SIZES = {
    "#10-32 UNF": {
        "major_dia_m":          0.190 * IN,
        "tensile_stress_area_m2": 0.0175 * (IN ** 2),
    },
    "#1/4-28 UNF": {
        "major_dia_m":          0.250 * IN,
        "tensile_stress_area_m2": 0.0364 * (IN ** 2),
    },
}
NOMINAL_BOLT_SIZE = "#10-32 UNF"
NOMINAL_PAD_DIA_M = 0.0120
NOMINAL_N_BOLTS = 8
NOMINAL_PRELOAD_FACTOR = 0.70
NOMINAL_BOLT_MATL = "A286 stainless (typical aerospace)"

TARGET_SF = 2.0


# ============================================================
# Mechanics
# ============================================================
def proof_load(A_t_m2, material_dict):
    return PROOF_FACTOR * A_t_m2 * material_dict["tensile_MPa"] * 1e6


def evaluate_joint(
    bolt_size=NOMINAL_BOLT_SIZE,
    material_name=NOMINAL_BOLT_MATL,
    preload_factor=NOMINAL_PRELOAD_FACTOR,
    pad_dia_m=NOMINAL_PAD_DIA_M,
    n_bolts=NOMINAL_N_BOLTS,
    F_radial_max_N=None,
):
    """Returns yield SF, separation SF, pad compression SF for the
    bolt-joint under the worst-case external load."""
    if F_radial_max_N is None:
        F_radial_max_N = 612.4  # from main screening, max rock event

    bs = BOLT_SIZES[bolt_size]
    matl = BOLT_MATERIALS[material_name]
    A_t = bs["tensile_stress_area_m2"]
    bolt_dia = bs["major_dia_m"]

    # External per-bolt loads (worst case)
    T_max = F_radial_max_N * MU_MAX * WHEEL_RADIUS_M
    F_lateral = F_radial_max_N * LATERAL_FRACTION
    M_axial = F_radial_max_N * AXIAL_OFFSET_M
    F_tension_per_bolt = 2.0 * M_axial / (n_bolts * BOLT_CIRCLE_RADIUS_M)
    F_shear_radial = math.sqrt(F_radial_max_N ** 2 + F_lateral ** 2) / n_bolts
    F_shear_torque = T_max / (n_bolts * BOLT_CIRCLE_RADIUS_M)
    F_shear_per_bolt = math.sqrt(F_shear_radial ** 2 + F_shear_torque ** 2)

    # Bolt mechanics
    F_proof = proof_load(A_t, matl)
    F_pre = preload_factor * F_proof
    F_bolt = F_pre + JOINT_STIFFNESS_RATIO_C * F_tension_per_bolt
    sigma_bolt_MPa = F_bolt / A_t / 1e6
    yield_SF = matl["yield_MPa"] / sigma_bolt_MPa

    F_separation = F_pre / (1.0 - JOINT_STIFFNESS_RATIO_C)
    separation_SF = (
        F_separation / F_tension_per_bolt
        if F_tension_per_bolt > 0 else float("inf")
    )

    # Pad compression
    A_pad = math.pi / 4.0 * (pad_dia_m ** 2 - bolt_dia ** 2)
    pad_compression_MPa = F_pre / A_pad / 1e6
    pad_SF = COMPOSITE_COMPRESSION_ALLOWABLE_MPa / pad_compression_MPa

    shear_capacity_N = matl["shear_MPa"] * A_t * 1e6
    shear_SF = (
        shear_capacity_N / F_shear_per_bolt
        if F_shear_per_bolt > 0 else float("inf")
    )

    return {
        "bolt_size":          bolt_size,
        "material":           material_name,
        "preload_factor":     preload_factor,
        "pad_dia_mm":         pad_dia_m * 1000,
        "n_bolts":            n_bolts,
        "preload_N":          F_pre,
        "tension_per_bolt_N": F_tension_per_bolt,
        "shear_per_bolt_N":   F_shear_per_bolt,
        "bolt_stress_MPa":    sigma_bolt_MPa,
        "yield_SF":           yield_SF,
        "shear_SF":           shear_SF,
        "separation_SF":      separation_SF,
        "pad_compression_MPa": pad_compression_MPa,
        "pad_SF":             pad_SF,
    }


def hits_target(r, target=TARGET_SF):
    return (r["yield_SF"] >= target) and (r["pad_SF"] >= target)


# ============================================================
# Main
# ============================================================
def main():
    os.makedirs("plots", exist_ok=True)

    print("=" * 64)
    print("Design iteration: hub bolt joint margins")
    print("=" * 64)

    # Get peak load from main screening model
    print("Running screening model to extract peak load...")
    df, summary = run_screening()
    F_radial_max = float(summary["max_load_N_seen"])
    print(f"  Max radial load per wheel: {F_radial_max:.1f} N")
    print()

    print(f"Baseline joint: {NOMINAL_BOLT_SIZE}, "
          f"{NOMINAL_BOLT_MATL}, "
          f"{int(NOMINAL_PRELOAD_FACTOR*100)}% preload, "
          f"{NOMINAL_PAD_DIA_M*1000:.0f} mm pad, "
          f"{NOMINAL_N_BOLTS} bolts")
    baseline = evaluate_joint(F_radial_max_N=F_radial_max)
    print(f"  Yield SF:        {baseline['yield_SF']:.2f}")
    print(f"  Pad SF:          {baseline['pad_SF']:.2f}")
    print(f"  Separation SF:   {baseline['separation_SF']:.1f}")
    print(f"  Shear SF:        {baseline['shear_SF']:.1f}")
    print(f"  -> hits target {TARGET_SF:.1f} on both:  "
          f"{'✓' if hits_target(baseline) else '✗'}")
    print()

    # Each design change alone
    print(f"Single-variable changes vs target SF >= {TARGET_SF:.1f}:")
    print(f"{'Change':<55}  {'yield SF':>9}  {'pad SF':>8}  "
          f"{'sep SF':>8}  {'both >= 2?':>11}")
    print("-" * 92)
    changes = [
        ("(P) Preload 70% -> 50% proof",
         dict(preload_factor=0.50)),
        ("(P) Preload 70% -> 60% proof",
         dict(preload_factor=0.60)),
        ("(D) Pad-boss 12 -> 14 mm",
         dict(pad_dia_m=0.014)),
        ("(D) Pad-boss 12 -> 16 mm",
         dict(pad_dia_m=0.016)),
        ("(D) Pad-boss 12 -> 18 mm",
         dict(pad_dia_m=0.018)),
        ("(M) Ti-6Al-4V instead of A286",
         dict(material_name="Ti-6Al-4V (lightweight)")),
        ("(S) Upsize bolts #10-32 -> #1/4-28",
         dict(bolt_size="#1/4-28 UNF")),
        ("(N) More bolts 8 -> 10",
         dict(n_bolts=10)),
        ("(N) More bolts 8 -> 12",
         dict(n_bolts=12)),
    ]
    results_alone = []
    for label, kw in changes:
        r = evaluate_joint(F_radial_max_N=F_radial_max, **kw)
        marker = "✓" if hits_target(r) else "✗"
        print(f"{label:<55}  {r['yield_SF']:>9.2f}  {r['pad_SF']:>8.2f}  "
              f"{r['separation_SF']:>8.1f}  {marker:>11}")
        results_alone.append({"label": label, **{
            k: round(v, 3) if isinstance(v, float) else v
            for k, v in r.items()
        }})
    print()

    # Combinations
    print("Stacked combinations:")
    print(f"{'Stack':<55}  {'yield SF':>9}  {'pad SF':>8}  "
          f"{'both >= 2?':>11}")
    print("-" * 84)
    combos = [
        ("(P 50%) + (D 14 mm)",
         dict(preload_factor=0.50, pad_dia_m=0.014)),
        ("(P 50%) + (D 16 mm)",
         dict(preload_factor=0.50, pad_dia_m=0.016)),
        ("(P 50%) + (M Ti-6Al-4V)",
         dict(preload_factor=0.50, material_name="Ti-6Al-4V (lightweight)")),
        ("(P 50%) + (D 14 mm) + (M Ti)",
         dict(preload_factor=0.50, pad_dia_m=0.014,
              material_name="Ti-6Al-4V (lightweight)")),
        ("(P 50%) + (D 16 mm) + (M Ti)",
         dict(preload_factor=0.50, pad_dia_m=0.016,
              material_name="Ti-6Al-4V (lightweight)")),
        ("(P 60%) + (D 16 mm)",
         dict(preload_factor=0.60, pad_dia_m=0.016)),
        ("(P 60%) + (D 16 mm) + (N 10)",
         dict(preload_factor=0.60, pad_dia_m=0.016, n_bolts=10)),
        ("(M Ti) + (N 10) + (D 14 mm) (preload nominal 70%)",
         dict(material_name="Ti-6Al-4V (lightweight)",
              n_bolts=10, pad_dia_m=0.014)),
    ]
    results_combos = []
    for label, kw in combos:
        r = evaluate_joint(F_radial_max_N=F_radial_max, **kw)
        marker = "✓" if hits_target(r) else "✗"
        print(f"{label:<55}  {r['yield_SF']:>9.2f}  {r['pad_SF']:>8.2f}  "
              f"{marker:>11}")
        results_combos.append({"label": label, **{
            k: round(v, 3) if isinstance(v, float) else v
            for k, v in r.items()
        }})
    print()

    # Minimum stack search
    print("Minimum-invasive design changes that hit both SFs >= 2.0:")
    print(f"{'Candidate':<55}  {'yield SF':>9}  {'pad SF':>8}")
    print("-" * 76)
    candidates = [
        ("(P) preload only -- minimum %",          {"_search": "preload"}),
        ("(D) pad-boss only -- minimum mm",        {"_search": "pad"}),
        ("(P 50%) + minimum pad-boss",             {"_search": "p50_pad"}),
        ("(M Ti) + minimum pad-boss",              {"_search": "ti_pad"}),
    ]
    min_stacks_found = []
    # (P) alone -- find the HIGHEST preload that still hits target
    # (= smallest reduction from the 70% baseline)
    found = False
    for pf in np.arange(0.70, 0.29, -0.01):
        r = evaluate_joint(F_radial_max_N=F_radial_max, preload_factor=pf)
        if hits_target(r):
            label = f"(P) alone, preload = {pf*100:.0f}% (max viable)"
            print(f"{label:<55}  {r['yield_SF']:>9.2f}  {r['pad_SF']:>8.2f}")
            min_stacks_found.append((label, r))
            found = True
            break
    if not found:
        label = "(P) alone -- no preload value works"
        print(f"{label:<55}  N/A")

    # (D) alone -- pad size cannot fix yield (preload-dominated)
    label = "(D) alone -- pad size alone cannot fix yield SF"
    print(f"{label:<55}  N/A")

    # (P) + (D 14 mm) -- find the highest preload with 14 mm pad
    for pf in np.arange(0.70, 0.29, -0.01):
        r = evaluate_joint(F_radial_max_N=F_radial_max,
                           preload_factor=pf, pad_dia_m=0.014)
        if hits_target(r):
            label = f"(P {pf*100:.0f}%) + (D 14 mm)"
            print(f"{label:<55}  {r['yield_SF']:>9.2f}  {r['pad_SF']:>8.2f}")
            min_stacks_found.append((label, r))
            break

    # (M Ti) + (P) -- find the highest preload with Ti
    for pf in np.arange(0.70, 0.29, -0.01):
        r = evaluate_joint(F_radial_max_N=F_radial_max,
                           material_name="Ti-6Al-4V (lightweight)",
                           preload_factor=pf)
        if hits_target(r):
            label = f"(M Ti) + (P {pf*100:.0f}%), 12 mm pad (no D change)"
            print(f"{label:<55}  {r['yield_SF']:>9.2f}  {r['pad_SF']:>8.2f}")
            min_stacks_found.append((label, r))
            break
    print()

    # CSV outputs
    pd.DataFrame(results_alone).to_csv(
        "bolt_joint_iteration_alone.csv", index=False
    )
    pd.DataFrame(results_combos).to_csv(
        "bolt_joint_iteration_combos.csv", index=False
    )
    print("Wrote bolt_joint_iteration_alone.csv")
    print("Wrote bolt_joint_iteration_combos.csv")
    print()

    # Plot: SF vs preload, for three pad diameters
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    preload_grid = np.linspace(0.30, 0.90, 25)
    ax = axes[0]
    for pd_mm, color in zip((12, 14, 16, 18),
                            ("tab:blue", "tab:orange", "tab:green", "tab:red")):
        SFs = []
        for pf in preload_grid:
            r = evaluate_joint(F_radial_max_N=F_radial_max,
                               preload_factor=pf, pad_dia_m=pd_mm/1000.0)
            SFs.append(r["yield_SF"])
        ax.plot(preload_grid * 100, SFs, label=f"pad {pd_mm} mm",
                color=color, linewidth=2)
    ax.axhline(2.0, color="green", linestyle="--", alpha=0.7,
               label="target SF = 2.0")
    ax.set_xlabel("Preload (% of proof)")
    ax.set_ylabel("Bolt yield SF")
    ax.set_title("Bolt yield SF vs preload (A286)")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(fontsize=9)

    ax = axes[1]
    for pd_mm, color in zip((12, 14, 16, 18),
                            ("tab:blue", "tab:orange", "tab:green", "tab:red")):
        SFs = []
        for pf in preload_grid:
            r = evaluate_joint(F_radial_max_N=F_radial_max,
                               preload_factor=pf, pad_dia_m=pd_mm/1000.0)
            SFs.append(r["pad_SF"])
        ax.plot(preload_grid * 100, SFs, label=f"pad {pd_mm} mm",
                color=color, linewidth=2)
    ax.axhline(2.0, color="green", linestyle="--", alpha=0.7,
               label="target SF = 2.0")
    ax.set_xlabel("Preload (% of proof)")
    ax.set_ylabel("Pad compression SF")
    ax.set_title("Pad compression SF vs preload (A286)")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(fontsize=9)

    fig.tight_layout()
    fig.savefig("plots/bolt_joint_iteration.png", dpi=120)
    print("Wrote plots/bolt_joint_iteration.png")
    print()

    # Recommendation
    print("=" * 64)
    print("RECOMMENDATION")
    print("=" * 64)
    # Pick the simplest VALID stack: (P 50%) + Ti-6Al-4V bolts
    # (a single-material change + a preload-spec change; no composite
    # layout change, no bolt-size change, no bolt-count change)
    recommended = evaluate_joint(
        F_radial_max_N=F_radial_max,
        preload_factor=0.50,
        material_name="Ti-6Al-4V (lightweight)",
    )
    assert hits_target(recommended), \
        "recommended stack does not actually meet target"

    print(f"Recommended design changes (least invasive set that hits "
          f"both SFs >= {TARGET_SF:.1f}):")
    print(f"  (M) Switch bolt material A286 -> Ti-6Al-4V")
    print(f"  (P) Reduce bolt preload from 70% -> 50% of proof load")
    print(f"  No change to bolt size, pad diameter, bolt count, or")
    print(f"  composite hub layout.")
    print()
    print(f"Resulting margins:")
    print(f"  Yield SF:        {recommended['yield_SF']:.2f}  (was 1.38)")
    print(f"  Pad SF:          {recommended['pad_SF']:.2f}  (was 1.82)")
    print(f"  Separation SF:   {recommended['separation_SF']:.1f}  "
          f"(was 39 -- still ample)")
    print(f"  Shear SF:        {recommended['shear_SF']:.1f}")
    print()
    print(f"Mass / process / cost impact:")
    print(f"  - Ti-6Al-4V bolts (M): ~40% lighter than A286 stainless")
    print(f"    (~5-10 g savings across 10 fasteners); higher unit cost")
    print(f"    but smaller quantity; standard aerospace fastener spec")
    print(f"  - Preload change (P): zero hardware change; tighten with")
    print(f"    a calibrated torque wrench or use load-indicating washers")
    print()
    print(f"Alternative valid stacks:")
    for label, r in min_stacks_found:
        print(f"  - {label}: yield SF = {r['yield_SF']:.2f}, "
              f"pad SF = {r['pad_SF']:.2f}")
    print()
    print(f"This recommendation should be validated by 3D FEM of the")
    print(f"modified joint and by re-running the launch-load check with")
    print(f"the new preload (lower preload reduces clamp force, which")
    print(f"could affect joint behaviour under random vibration).")


if __name__ == "__main__":
    main()
