
"""
Hub bolt joint screening check.

The wheel attaches to the suspension through a bolt pattern on the
composite hub adapter plate. From the AURORA-Mono build spec:

  Bolt circle:     Ø 4.000 in (101.60 mm), 8x #10-32 UNF THRU
  Jack bolts:      2x #10-32 UNF THRU on the same bolt circle
  Alignment pins:  2x Ø 0.2502 in (6.356 mm) on the same bolt circle
  Hub plate:       6.0 mm composite (PEKK-CNT/CF) with 12.0 mm Ø
                   pad bosses at each hole

Mounted on the rover suspension, the joint sees:
  - Radial load    F_R: from wheel-ground contact, peaks at the
                        max rock-event load (~612 N)
  - Drive torque   T:   F_R * mu_max * wheel_radius
  - Lateral load   F_L: estimated as 30% of F_R during cornering
  - Axial moment   M:   F_R * axial_offset (load is offset from
                        the bolt plane by ~1/2 wheel width)

What this check covers:
  - Preloaded-bolt mechanics (preload, joint stiffness ratio C,
    bolt tension under external load, separation check, yield SF)
  - Combined per-bolt shear from torque + radial
  - Bearing stress in the composite plate at each bolt
  - Compressive crushing of the pad boss under bolt preload
  - Pin shear capacity (alignment pins as shear-rated members)
  - Sensitivity on bolt grade (A286 vs Ti-6Al-4V vs 316SS)
    and preload level (50-90% of proof)

What this check does NOT cover:
  - 3D FEM of the joint with realistic load distribution
  - Non-uniform bolt load sharing (real distribution depends on
    relative stiffness, which we approximate as uniform)
  - Bolt fatigue under variable-amplitude rotation cycles with
    proper Miner's rule (preload swamps cyclic stress here, but a
    full analysis would confirm)
  - Thermal effects on preload (lunar diurnal cycle would relax
    preload through PEKK creep at the pad boss)
  - Galling, fretting, cold welding, embedment relaxation
  - Pad-boss compression creep under sustained preload at +127 C
  - Stress concentration at the hole edge in the composite
  - Composite delamination from bolt-induced bearing stress
"""

import math
import os
import pandas as pd

from aurora_mono_screening_model import run_screening


# ============================================================
# Joint geometry from the AURORA-Mono build spec
# ============================================================
IN = 0.0254

BOLT_CIRCLE_DIA_IN = 4.000
BOLT_CIRCLE_RADIUS_M = (BOLT_CIRCLE_DIA_IN * IN) / 2.0
N_MOUNTING_BOLTS = 8
N_JACK_BOLTS = 2
N_ALIGNMENT_PINS = 2

HUB_PLATE_THICKNESS_M = 0.0060           # 6.0 mm composite
PAD_BOSS_DIA_M = 0.0120                  # 12.0 mm pad boss at each hole

# #10-32 UNF thread spec
BOLT_MAJOR_DIA_IN = 0.190
BOLT_MAJOR_DIA_M = BOLT_MAJOR_DIA_IN * IN
# Tensile stress area for #10-32 UNF (Machinery's Handbook)
BOLT_TENSILE_STRESS_AREA_M2 = 0.0175 * (IN ** 2)   # ≈ 11.3 mm²

# Alignment pin
PIN_DIA_M = 0.2502 * IN                            # 6.356 mm
PIN_SHEAR_AREA_M2 = math.pi * (PIN_DIA_M ** 2) / 4.0


# ============================================================
# Wheel + rover params (consistent with main screening model)
# ============================================================
WHEEL_OD_IN = 18.0
WHEEL_WIDTH_IN = 8.0
WHEEL_RADIUS_M = (WHEEL_OD_IN * IN) / 2.0
WHEEL_WIDTH_M = WHEEL_WIDTH_IN * IN

# Maximum traction coefficient (from the main screening model)
MU_MAX = 0.55

# Load axial offset from the bolt plane. Conservative: assume the
# resultant ground reaction acts at the wheel midplane, which sits
# half a wheel-width from the bolt plane.
AXIAL_OFFSET_M = WHEEL_WIDTH_M / 2.0

# Lateral load fraction (cornering / side impact)
LATERAL_FRACTION = 0.30


# ============================================================
# Material properties
# ============================================================
# Aerospace bolt candidates
BOLT_MATERIALS = {
    "A286 stainless (typical aerospace)": {
        "tensile_MPa": 1240,
        "yield_MPa":   1030,
        "shear_MPa":    745,
    },
    "Ti-6Al-4V (lightweight)": {
        "tensile_MPa": 950,
        "yield_MPa":   880,
        "shear_MPa":   570,
    },
    "316 stainless (corrosion-resistant)": {
        "tensile_MPa": 580,
        "yield_MPa":   240,
        "shear_MPa":   350,
    },
}
NOMINAL_BOLT_MATL = "A286 stainless (typical aerospace)"

# Composite hub plate (PEKK-CNT/CF)
COMPOSITE_BEARING_ALLOWABLE_MPa = 200.0   # bolt-bearing on hole edge
COMPOSITE_COMPRESSION_ALLOWABLE_MPa = 160.0  # uniaxial compression on pad


# ============================================================
# Bolt joint mechanics
# ============================================================
JOINT_STIFFNESS_RATIO_C = 0.30   # k_bolt / (k_bolt + k_joint), composite joint
PROOF_FACTOR = 0.85              # F_proof = 0.85 * A_t * sigma_tensile
PRELOAD_FACTOR_NOMINAL = 0.70    # F_preload = 0.70 * F_proof


def proof_load_N(matl):
    return PROOF_FACTOR * BOLT_TENSILE_STRESS_AREA_M2 * matl["tensile_MPa"] * 1e6


def preload_N(matl, preload_factor=PRELOAD_FACTOR_NOMINAL):
    return preload_factor * proof_load_N(matl)


def bolt_check(F_external_axial_N, F_external_shear_N, matl,
               preload_factor=PRELOAD_FACTOR_NOMINAL,
               C=JOINT_STIFFNESS_RATIO_C):
    """Standard preloaded-bolt mechanics. Returns SFs and key values."""
    F_proof = proof_load_N(matl)
    F_pre = preload_N(matl, preload_factor)
    # Bolt total tension under external axial pull
    F_bolt = F_pre + C * F_external_axial_N
    sigma_bolt_MPa = F_bolt / BOLT_TENSILE_STRESS_AREA_M2 / 1e6
    # Joint clamp force remaining under external pull
    F_clamp = F_pre - (1 - C) * F_external_axial_N
    F_separation = F_pre / (1 - C)

    # Direct shear check (separate failure mode)
    shear_capacity_N = matl["shear_MPa"] * BOLT_TENSILE_STRESS_AREA_M2 * 1e6
    shear_SF = (
        shear_capacity_N / F_external_shear_N
        if F_external_shear_N > 0 else float("inf")
    )

    return {
        "preload_N":           F_pre,
        "proof_load_N":        F_proof,
        "bolt_tension_N":      F_bolt,
        "bolt_stress_MPa":     sigma_bolt_MPa,
        "yield_SF":            matl["yield_MPa"] / sigma_bolt_MPa,
        "tensile_SF":          matl["tensile_MPa"] / sigma_bolt_MPa,
        "remaining_clamp_N":   F_clamp,
        "separation_load_N":   F_separation,
        "separation_SF":       (
            F_separation / F_external_axial_N
            if F_external_axial_N > 0 else float("inf")
        ),
        "shear_capacity_N":    shear_capacity_N,
        "shear_SF":            shear_SF,
    }


# ============================================================
# Load distribution onto the bolt pattern
# ============================================================
def per_bolt_loads(F_radial_N, T_torque_Nm, F_lateral_N,
                   bolt_circle_radius_m=BOLT_CIRCLE_RADIUS_M,
                   n_bolts=N_MOUNTING_BOLTS,
                   axial_offset_m=AXIAL_OFFSET_M):
    """Decompose joint loads into per-bolt tension and shear.

    Tension comes from the prying moment created by axial offset of the
    radial load from the bolt plane (bolts on opposite sides take tension
    and compression). Shear comes from radial load shared uniformly plus
    torque-induced tangential load.
    """
    # Moment from axial offset
    M_axial = F_radial_N * axial_offset_m  # N·m
    # Tension on the most-loaded bolt: 2*M / (n * r_bc)
    # (resultant of moment reacted by the bolt pattern at radius r_bc)
    F_tension_per_bolt = 2.0 * M_axial / (n_bolts * bolt_circle_radius_m)

    # Direct shear from radial + lateral load, uniform sharing
    F_resultant_in_plane = math.sqrt(F_radial_N ** 2 + F_lateral_N ** 2)
    F_shear_radial = F_resultant_in_plane / n_bolts

    # Shear from drive torque
    F_shear_torque = T_torque_Nm / (n_bolts * bolt_circle_radius_m)

    # Combined shear per bolt (worst case: vectors add)
    F_shear_total = math.sqrt(F_shear_radial ** 2 + F_shear_torque ** 2)

    return {
        "tension_per_bolt_N": F_tension_per_bolt,
        "shear_per_bolt_N":   F_shear_total,
        "shear_from_radial_N": F_shear_radial,
        "shear_from_torque_N": F_shear_torque,
        "drive_torque_Nm":    T_torque_Nm,
        "moment_about_bolt_plane_Nm": M_axial,
    }


# ============================================================
# Composite-plate checks
# ============================================================
def bearing_stress_MPa(F_shear_N, bolt_dia_m, plate_thickness_m):
    """Bolt-shank bearing stress on the composite hole edge."""
    A_bearing = bolt_dia_m * plate_thickness_m
    return F_shear_N / A_bearing / 1e6


def pad_boss_compressive_stress_MPa(F_preload_N, pad_dia_m, bolt_dia_m):
    """Compressive stress on the 12 mm pad boss under bolt preload
    (annular area: pad outer minus bolt hole)."""
    A_pad = math.pi / 4.0 * (pad_dia_m ** 2 - bolt_dia_m ** 2)
    return F_preload_N / A_pad / 1e6


# ============================================================
# Main
# ============================================================
def main():
    print("=" * 64)
    print("Hub bolt joint screening check")
    print("=" * 64)
    print(f"Joint geometry:")
    print(f"  Bolt circle:        Ø{BOLT_CIRCLE_DIA_IN:.3f} in "
          f"({BOLT_CIRCLE_RADIUS_M*2*1000:.1f} mm)")
    print(f"  Mounting bolts:     {N_MOUNTING_BOLTS}x #10-32 UNF "
          f"(A_t = {BOLT_TENSILE_STRESS_AREA_M2*1e6:.2f} mm²)")
    print(f"  Alignment pins:     {N_ALIGNMENT_PINS}x Ø"
          f"{PIN_DIA_M*1000:.3f} mm "
          f"(A_pin = {PIN_SHEAR_AREA_M2*1e6:.2f} mm²)")
    print(f"  Hub plate:          {HUB_PLATE_THICKNESS_M*1000:.1f} mm "
          f"composite with Ø{PAD_BOSS_DIA_M*1000:.1f} mm pad bosses")
    print()

    # Pull peak loads from the main screening model
    print("Running screening model to extract peak loads...")
    df, summary = run_screening()
    F_radial_static = float(summary["static_load_per_wheel_N"])
    F_radial_max = float(summary["max_load_N_seen"])
    T_max_Nm = F_radial_max * MU_MAX * WHEEL_RADIUS_M
    F_lateral_max = F_radial_max * LATERAL_FRACTION

    print()
    print("Mission loads at the joint (worst case):")
    print(f"  Static radial F_R:    {F_radial_static:>6.1f} N")
    print(f"  Max radial F_R:       {F_radial_max:>6.1f} N "
          f"(worst rock event)")
    print(f"  Drive torque T:       {T_max_Nm:>6.2f} N·m  "
          f"(= F_R × μ_max × R = {F_radial_max:.0f} × {MU_MAX} "
          f"× {WHEEL_RADIUS_M*1000:.0f} mm)")
    print(f"  Lateral F_L:          {F_lateral_max:>6.1f} N  "
          f"({LATERAL_FRACTION:.0%} of F_R, cornering estimate)")
    print()

    # Decompose to per-bolt
    pb_max = per_bolt_loads(F_radial_max, T_max_Nm, F_lateral_max)
    pb_static = per_bolt_loads(
        F_radial_static, F_radial_static * MU_MAX * WHEEL_RADIUS_M, 0.0
    )

    print("Per-bolt loads (uniform sharing across 8 mounting bolts):")
    print(f"{'Case':<22}  {'F_tension':>11}  {'F_shear':>10}  "
          f"{'shear from F_R':>16}  {'shear from T':>14}")
    for label, pb in (("Static cruise", pb_static), ("Max event", pb_max)):
        print(f"{label:<22}  {pb['tension_per_bolt_N']:>9.1f} N  "
              f"{pb['shear_per_bolt_N']:>8.1f} N  "
              f"{pb['shear_from_radial_N']:>14.1f} N  "
              f"{pb['shear_from_torque_N']:>12.1f} N")
    print()

    # Bolt mechanics (nominal: A286, 70% proof preload)
    matl = BOLT_MATERIALS[NOMINAL_BOLT_MATL]
    chk_static = bolt_check(
        pb_static["tension_per_bolt_N"],
        pb_static["shear_per_bolt_N"],
        matl,
    )
    chk_max = bolt_check(
        pb_max["tension_per_bolt_N"],
        pb_max["shear_per_bolt_N"],
        matl,
    )

    print(f"Bolt mechanics ({NOMINAL_BOLT_MATL}, "
          f"preload = {PRELOAD_FACTOR_NOMINAL:.0%} proof, "
          f"joint stiffness ratio C = {JOINT_STIFFNESS_RATIO_C:.2f}):")
    print(f"  Proof load:           {chk_max['proof_load_N']:>7.0f} N "
          f"({chk_max['proof_load_N']*0.2248:.0f} lbf)")
    print(f"  Preload:              {chk_max['preload_N']:>7.0f} N "
          f"({chk_max['preload_N']*0.2248:.0f} lbf)")
    print()
    print(f"{'Case':<14}  {'F_bolt':>9}  {'σ_bolt':>9}  "
          f"{'yield SF':>9}  {'tension SF':>11}  {'shear SF':>10}  "
          f"{'separation SF':>14}")
    for label, chk in (("Static cruise", chk_static), ("Max event", chk_max)):
        sep_str = (
            "∞" if math.isinf(chk["separation_SF"])
            else f"{chk['separation_SF']:.1f}"
        )
        print(f"{label:<14}  {chk['bolt_tension_N']:>7.0f} N  "
              f"{chk['bolt_stress_MPa']:>7.0f} MPa  "
              f"{chk['yield_SF']:>9.2f}  "
              f"{chk['tensile_SF']:>11.2f}  "
              f"{chk['shear_SF']:>10.1f}  "
              f"{sep_str:>14}")
    print()

    # Composite-plate checks
    bearing_max_MPa = bearing_stress_MPa(
        pb_max["shear_per_bolt_N"], BOLT_MAJOR_DIA_M, HUB_PLATE_THICKNESS_M
    )
    bearing_SF = COMPOSITE_BEARING_ALLOWABLE_MPa / bearing_max_MPa

    pad_compression_MPa = pad_boss_compressive_stress_MPa(
        chk_max["preload_N"], PAD_BOSS_DIA_M, BOLT_MAJOR_DIA_M
    )
    pad_SF = COMPOSITE_COMPRESSION_ALLOWABLE_MPa / pad_compression_MPa

    print("Composite hub plate checks:")
    print(f"  Bolt-shank bearing on hole edge (max event):")
    print(f"    σ_bearing = {bearing_max_MPa:>6.1f} MPa  "
          f"vs allowable {COMPOSITE_BEARING_ALLOWABLE_MPa:.0f} MPa  "
          f"→ SF = {bearing_SF:.1f}")
    print(f"  Pad boss compression under preload "
          f"(annular {PAD_BOSS_DIA_M*1000:.0f}-{BOLT_MAJOR_DIA_M*1000:.1f} mm):")
    print(f"    σ_compression = {pad_compression_MPa:>6.1f} MPa  "
          f"vs allowable {COMPOSITE_COMPRESSION_ALLOWABLE_MPa:.0f} MPa  "
          f"→ SF = {pad_SF:.1f}")
    print()

    # Pin shear capacity
    print("Alignment pin shear capacity (carbon-steel pin, typical):")
    pin_shear_capacity_N = 0.6 * 800.0e6 * PIN_SHEAR_AREA_M2  # ~800 MPa tensile
    pin_demand_N = pb_max["shear_per_bolt_N"] * (
        N_MOUNTING_BOLTS / N_ALIGNMENT_PINS
    )
    print(f"  Per-pin capacity:      {pin_shear_capacity_N:>7.0f} N")
    print(f"  Per-pin demand (worst, if pins take 100% shear): "
          f"{pin_demand_N:>4.0f} N")
    print(f"  Pin shear SF:          {pin_shear_capacity_N/pin_demand_N:>5.0f}")
    print()

    # ============================================================
    # Sensitivity sweep
    # ============================================================
    print("Sensitivity sweep on bolt material and preload level:")
    print(f"{'Material':<40}  {'preload %':>10}  "
          f"{'yield SF':>9}  {'sep SF':>8}  {'pad SF':>8}")
    sens_rows = []
    for matl_name, matl_props in BOLT_MATERIALS.items():
        for preload_pct in (0.50, 0.70, 0.90):
            chk = bolt_check(
                pb_max["tension_per_bolt_N"],
                pb_max["shear_per_bolt_N"],
                matl_props,
                preload_factor=preload_pct,
            )
            pad_MPa = pad_boss_compressive_stress_MPa(
                chk["preload_N"], PAD_BOSS_DIA_M, BOLT_MAJOR_DIA_M
            )
            pad_local_SF = COMPOSITE_COMPRESSION_ALLOWABLE_MPa / pad_MPa
            sep_str = (
                "inf" if math.isinf(chk["separation_SF"])
                else f"{chk['separation_SF']:.1f}"
            )
            print(f"{matl_name:<40}  {preload_pct:>9.0%}  "
                  f"{chk['yield_SF']:>9.2f}  {sep_str:>8}  "
                  f"{pad_local_SF:>8.2f}")
            sens_rows.append({
                "material":              matl_name,
                "preload_pct_of_proof":  preload_pct,
                "preload_N":             round(chk["preload_N"], 1),
                "bolt_tension_N":        round(chk["bolt_tension_N"], 1),
                "yield_SF":              round(chk["yield_SF"], 3),
                "tensile_SF":            round(chk["tensile_SF"], 3),
                "shear_SF":              (
                    None if math.isinf(chk["shear_SF"])
                    else round(chk["shear_SF"], 2)
                ),
                "separation_SF":         (
                    None if math.isinf(chk["separation_SF"])
                    else round(chk["separation_SF"], 2)
                ),
                "pad_compression_MPa":   round(pad_MPa, 2),
                "pad_compression_SF":    round(pad_local_SF, 2),
            })
    print()

    # ============================================================
    # CSV outputs
    # ============================================================
    summary_row = {
        "bolt_circle_dia_mm":           BOLT_CIRCLE_DIA_IN * 25.4,
        "n_mounting_bolts":             N_MOUNTING_BOLTS,
        "bolt_size":                    "#10-32 UNF",
        "bolt_tensile_area_mm2":        round(
            BOLT_TENSILE_STRESS_AREA_M2 * 1e6, 3
        ),
        "hub_plate_thickness_mm":       HUB_PLATE_THICKNESS_M * 1000,
        "pad_boss_dia_mm":              PAD_BOSS_DIA_M * 1000,
        "nominal_bolt_material":        NOMINAL_BOLT_MATL,
        "preload_factor":               PRELOAD_FACTOR_NOMINAL,
        "joint_stiffness_ratio_C":      JOINT_STIFFNESS_RATIO_C,
        "max_radial_load_N":            round(F_radial_max, 1),
        "max_drive_torque_Nm":          round(T_max_Nm, 2),
        "tension_per_bolt_max_N":       round(
            pb_max["tension_per_bolt_N"], 1
        ),
        "shear_per_bolt_max_N":         round(
            pb_max["shear_per_bolt_N"], 1
        ),
        "bolt_preload_N":               round(chk_max["preload_N"], 1),
        "bolt_stress_max_MPa":          round(chk_max["bolt_stress_MPa"], 1),
        "bolt_yield_SF_max":            round(chk_max["yield_SF"], 3),
        "bolt_separation_SF":           (
            None if math.isinf(chk_max["separation_SF"])
            else round(chk_max["separation_SF"], 2)
        ),
        "bolt_shear_SF":                round(chk_max["shear_SF"], 2),
        "composite_bearing_MPa":        round(bearing_max_MPa, 2),
        "composite_bearing_SF":         round(bearing_SF, 2),
        "pad_compression_MPa":          round(pad_compression_MPa, 2),
        "pad_compression_SF":           round(pad_SF, 2),
    }
    pd.DataFrame([summary_row]).to_csv(
        "bolt_joint_check_summary.csv", index=False
    )
    pd.DataFrame(sens_rows).to_csv(
        "bolt_joint_check_sensitivity.csv", index=False
    )
    print("Wrote bolt_joint_check_summary.csv")
    print("Wrote bolt_joint_check_sensitivity.csv")
    print()

    # ============================================================
    # Verdict
    # ============================================================
    print("=" * 64)
    print("VERDICT")
    print("=" * 64)
    governing = "bolt yield" if chk_max["yield_SF"] <= pad_SF else "pad compression"
    governing_SF = min(chk_max["yield_SF"], pad_SF)
    print(f"Governing margin: {governing} (SF = {governing_SF:.2f})")
    print()
    if governing_SF >= 1.5:
        v = ("Comfortable margin on the governing mode. The joint design "
             "(8x #10-32 + 2 jack bolts + 2 alignment pins on a 4-inch BC) "
             "is reasonable for the modeled loads.")
    elif governing_SF >= 1.0:
        v = ("Marginal SF on the governing mode. Consider larger bolts, "
             "higher-grade material, or larger pad bosses.")
    else:
        v = ("INSUFFICIENT margin. Redesign required.")
    print(v)
    print()
    print("Notes on what this screening DOES NOT capture:")
    print("  - PEKK pad-boss creep under sustained preload at +127 C "
          "would relax bolt clamp force over the lunar day. The pad")
    print("    compression SF reported here is initial only.")
    print("  - Thermal cycling of the bolt itself (steel vs composite "
          "differential expansion) would cycle preload.")
    print("  - Bolt fatigue under wheel-rotation cyclic loading -- the "
          "preload dominates, but full Goodman analysis is recommended.")
    print("  - 3D FEM would resolve non-uniform load sharing across the "
          "8 bolts and stress concentrations at the hole edge.")


if __name__ == "__main__":
    main()
