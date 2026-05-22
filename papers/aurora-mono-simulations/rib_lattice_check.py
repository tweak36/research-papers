
"""
Helical X-brace rib lattice screening check.

The lattice between the inner and outer skins is the wheel's primary
load-bearing core. Under wheel-ground contact loading, the lattice
carries shear from the outer skin (pushed inward at the contact patch)
to the inner skin (constrained by the hub spokes). This check evaluates
the lattice at screening fidelity.

What this DOES check:
- Per-rib compressive stress under tributary contact-patch loading
- Euler / Johnson buckling of a single rib spanning the 7 mm core
- Effective sandwich-core shear stress and modulus
- Volume fraction of lattice material vs typical aerospace honeycomb
- Sensitivity to contact patch size (how many ribs share the load)

What this does NOT check:
- Joint stresses at rib-to-skin connections (rib root may be critical)
- Non-uniform load distribution across ribs in the contact patch
- Torque transfer through the lattice (driving / braking)
- Lateral (axial) loading of the wheel
- Eigenmode analysis or natural frequencies
- Dynamic amplification under impact
- Anisotropy from the helix direction
- FEM-resolved stress concentrations at rib intersections
- Plasticity, creep, fatigue, fracture
"""

import math
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from aurora_mono_screening_model import run_screening


# ============================================================
# Geometry from the AURORA-Mono build spec
# ============================================================
IN = 0.0254

WHEEL_OD_IN = 16.8                  # rim OD (pre-tread)
WHEEL_WIDTH_IN = 8.0
WHEEL_OD_M = WHEEL_OD_IN * IN
WHEEL_WIDTH_M = WHEEL_WIDTH_IN * IN

SKIN_THICKNESS_M = 0.0012           # 1.20 mm each skin
CORE_HEIGHT_M = 0.0070              # 7.00 mm radial gap between skins

# Mean radius of the lattice mid-plane
RIM_OUTER_R_M = WHEEL_OD_M / 2.0
LATTICE_MEAN_R_M = (
    RIM_OUTER_R_M - SKIN_THICKNESS_M - CORE_HEIGHT_M / 2.0
)
LATTICE_MEAN_CIRC_M = 2.0 * math.pi * LATTICE_MEAN_R_M

# Rib geometry
N_RIBS_TOTAL = 48                   # 24 at +35° + 24 at -35°
N_RIBS_PER_DIRECTION = N_RIBS_TOTAL // 2
HELIX_ANGLE_DEG = 35.0              # from axial direction
HELIX_ANGLE_RAD = math.radians(HELIX_ANGLE_DEG)

RIB_WEB_THICKNESS_M = 0.0018        # 1.8 mm mid-span
RIB_DEPTH_M = CORE_HEIGHT_M          # spans full radial gap = 7 mm
RIB_CROSS_AREA_M2 = RIB_WEB_THICKNESS_M * RIB_DEPTH_M

# Helix arc length across the wheel width
RIB_HELIX_LENGTH_M = WHEEL_WIDTH_M / math.cos(HELIX_ANGLE_RAD)

# Lattice density: total material volume / nominal core volume
LATTICE_VOLUME_M3 = N_RIBS_TOTAL * RIB_HELIX_LENGTH_M * RIB_CROSS_AREA_M2
CORE_VOLUME_M3 = LATTICE_MEAN_CIRC_M * WHEEL_WIDTH_M * CORE_HEIGHT_M
LATTICE_VOLUME_FRACTION = LATTICE_VOLUME_M3 / CORE_VOLUME_M3


# ============================================================
# Material properties (estimated, not measured)
# ============================================================
E_PEKK_CNT_CF_PA = 30.0e9            # bulk modulus in-plane
NU_PEKK_CNT_CF = 0.35                # Poisson ratio (typical thermoplastic)
G_PEKK_CNT_CF_PA = E_PEKK_CNT_CF_PA / (2.0 * (1.0 + NU_PEKK_CNT_CF))
SIGMA_YIELD_MPa = 160.0              # PEKK-CNT/CF compressive/tensile allowable
SIGMA_PL_LIMIT_MPa = 0.5 * SIGMA_YIELD_MPa  # transition point for Johnson


# ============================================================
# Buckling formulas
# ============================================================
def euler_buckling_load_N(E_Pa, I_m4, L_m, K=1.0):
    """Euler critical load for a column with effective length factor K."""
    return (math.pi ** 2) * E_Pa * I_m4 / (K * L_m) ** 2


def johnson_critical_stress_MPa(sigma_yield_MPa, slenderness_ratio,
                                slenderness_at_pl_limit):
    """Johnson short-column transition stress."""
    if slenderness_ratio >= slenderness_at_pl_limit:
        return None
    sigma_pl_limit_Pa = 0.5 * sigma_yield_MPa * 1e6
    return (
        sigma_yield_MPa
        - (slenderness_ratio / slenderness_at_pl_limit) ** 2
        * (sigma_yield_MPa - sigma_pl_limit_Pa / 1e6)
    )


def rib_buckling_check(E_Pa, sigma_yield_MPa, web_t_m, depth_m, length_m):
    """Critical buckling stress for a single rib treated as a pin-ended
    column of length = core height. Uses Euler / Johnson transition."""
    A = web_t_m * depth_m
    I_min = (depth_m * web_t_m ** 3) / 12.0
    r_min = math.sqrt(I_min / A)
    slenderness = length_m / r_min
    # Cc transition
    Cc = math.sqrt(2.0 * (math.pi ** 2) * E_Pa / (sigma_yield_MPa * 1e6))
    if slenderness >= Cc:
        sigma_cr_Pa = (math.pi ** 2) * E_Pa / slenderness ** 2
        regime = "Euler (long column)"
    else:
        sigma_cr_MPa = (
            sigma_yield_MPa
            * (1.0 - (slenderness ** 2) / (2.0 * Cc ** 2))
        )
        sigma_cr_Pa = sigma_cr_MPa * 1e6
        regime = "Johnson (intermediate)"
    P_cr_N = sigma_cr_Pa * A
    return {
        "slenderness_ratio": slenderness,
        "Cc_transition": Cc,
        "regime": regime,
        "critical_stress_MPa": sigma_cr_Pa / 1e6,
        "critical_load_N": P_cr_N,
    }


# ============================================================
# Tributary load model
# ============================================================
def ribs_in_contact_patch(contact_patch_circ_mm, contact_patch_axial_mm,
                          circ_pitch_mm=20.0, axial_bay_mm=12.0):
    """Estimate how many rib intersections lie within the contact patch.

    Each ± direction has nodes spaced circ_pitch_mm circumferentially on
    each skin, and the rib spans axial_bay_mm across width. The number
    of ribs whose footprint overlaps the contact patch is roughly the
    product of patch dimensions / pitches, doubled for ±.
    """
    n_per_dir = max(
        1,
        (contact_patch_circ_mm / circ_pitch_mm)
        * (contact_patch_axial_mm / axial_bay_mm),
    )
    return int(round(n_per_dir * 2))


def per_rib_axial_load_N(load_total_N, n_ribs_in_contact,
                         helix_angle_rad=HELIX_ANGLE_RAD):
    """Per-rib axial force, accounting for the angle between the rib
    axis and the radial direction. The rib carries only the component
    of the radial load along its axis."""
    load_per_rib_radial = load_total_N / n_ribs_in_contact
    # Rib axis is in the helix; angle from radial direction... for a
    # rib spanning outer-to-inner skin at helix angle from axial,
    # the radial component requires resolving 3D geometry.
    # Conservative simplification: rib carries radial load directly
    # (worst case). Helix angle adds bending and shear which are not
    # captured here; the buckling check uses the same conservative load.
    return load_per_rib_radial


# ============================================================
# Main
# ============================================================
def main():
    os.makedirs("plots", exist_ok=True)

    print("=" * 64)
    print("Helical X-brace rib lattice screening check")
    print("=" * 64)
    print(f"Lattice geometry:")
    print(f"  Rim mean radius:           {LATTICE_MEAN_R_M*1000:.1f} mm")
    print(f"  Lattice circumference:     {LATTICE_MEAN_CIRC_M*1000:.1f} mm")
    print(f"  Width (axial):             {WHEEL_WIDTH_M*1000:.1f} mm")
    print(f"  Core height (radial gap):  {CORE_HEIGHT_M*1000:.1f} mm")
    print(f"  Total ribs:                {N_RIBS_TOTAL} "
          f"({N_RIBS_PER_DIRECTION} at +{HELIX_ANGLE_DEG:.0f}°, "
          f"{N_RIBS_PER_DIRECTION} at -{HELIX_ANGLE_DEG:.0f}°)")
    print(f"  Rib web thickness:         {RIB_WEB_THICKNESS_M*1000:.1f} mm")
    print(f"  Rib depth (radial):        {RIB_DEPTH_M*1000:.1f} mm")
    print(f"  Rib cross-section area:    "
          f"{RIB_CROSS_AREA_M2*1e6:.2f} mm² (per rib)")
    print(f"  Rib helix arc length:      {RIB_HELIX_LENGTH_M*1000:.1f} mm")
    print(f"  Lattice volume fraction:   "
          f"{LATTICE_VOLUME_FRACTION*100:.1f}% of nominal core volume")
    print(f"  (Typical aerospace honeycomb: 1-5% solid)")
    print()

    print(f"Material:  E = {E_PEKK_CNT_CF_PA/1e9:.0f} GPa, "
          f"G = {G_PEKK_CNT_CF_PA/1e9:.1f} GPa, "
          f"σ_yield = {SIGMA_YIELD_MPa:.0f} MPa")
    print()

    # === Single-rib buckling check ===
    buck = rib_buckling_check(
        E_PEKK_CNT_CF_PA, SIGMA_YIELD_MPa,
        RIB_WEB_THICKNESS_M, RIB_DEPTH_M, CORE_HEIGHT_M,
    )
    print("Single-rib buckling (treated as pin-ended column, L = core height):")
    print(f"  Slenderness ratio L/r:     {buck['slenderness_ratio']:.2f}")
    print(f"  Cc transition:             {buck['Cc_transition']:.2f}")
    print(f"  Regime:                    {buck['regime']}")
    print(f"  Critical stress:           {buck['critical_stress_MPa']:.1f} MPa")
    print(f"  Critical buckling load:    {buck['critical_load_N']:.0f} N per rib")
    print()

    # === Tributary load under mission loads ===
    print("Running screening model to extract mission load history...")
    df, summary = run_screening()
    static_load_N = float(summary["static_load_per_wheel_N"])
    max_load_N = float(summary["max_load_N_seen"])

    print(f"\nMission loads (from main screening model):")
    print(f"  Static load per wheel:     {static_load_N:.1f} N")
    print(f"  Max load per wheel:        {max_load_N:.1f} N "
          f"(worst rock event)")
    print()

    # === Per-rib stress for nominal contact patch ===
    NOMINAL_PATCH_CIRC_MM = 50.0
    NOMINAL_PATCH_AXIAL_MM = WHEEL_WIDTH_M * 1000
    n_ribs_nominal = ribs_in_contact_patch(
        NOMINAL_PATCH_CIRC_MM, NOMINAL_PATCH_AXIAL_MM,
    )
    print(f"Nominal contact patch: {NOMINAL_PATCH_CIRC_MM:.0f} mm circumferential "
          f"x {NOMINAL_PATCH_AXIAL_MM:.0f} mm axial -> "
          f"~{n_ribs_nominal} ribs in patch")
    print()

    cases = [
        ("Static load, nominal patch (uniform sharing)",
         static_load_N, n_ribs_nominal),
        ("Max load, nominal patch (uniform sharing)",
         max_load_N, n_ribs_nominal),
        ("Max load, narrow patch (~30 mm circ → fewer ribs)",
         max_load_N,
         ribs_in_contact_patch(30.0, NOMINAL_PATCH_AXIAL_MM)),
        ("Max load, very narrow patch (~10 mm circ)",
         max_load_N,
         ribs_in_contact_patch(10.0, NOMINAL_PATCH_AXIAL_MM)),
        ("Max load, only 1 rib bears it (worst conceivable)",
         max_load_N, 1),
    ]

    print(f"{'Case':<55}  {'load/rib':>9}  {'stress':>10}  "
          f"{'yield SF':>9}  {'buckl SF':>9}")
    print("-" * 100)
    case_rows = []
    for label, load_total_N, n_ribs in cases:
        load_per_rib = per_rib_axial_load_N(load_total_N, n_ribs)
        sigma_MPa = load_per_rib / (RIB_CROSS_AREA_M2 * 1e6)
        yield_SF = SIGMA_YIELD_MPa / sigma_MPa if sigma_MPa > 0 else float("inf")
        buckling_SF = (
            buck["critical_load_N"] / load_per_rib
            if load_per_rib > 0 else float("inf")
        )
        print(f"{label:<55}  {load_per_rib:>7.1f} N  "
              f"{sigma_MPa:>7.2f} MPa  {yield_SF:>9.1f}  {buckling_SF:>9.1f}")
        case_rows.append({
            "case": label,
            "load_total_N": round(load_total_N, 2),
            "n_ribs_sharing": n_ribs,
            "load_per_rib_N": round(load_per_rib, 2),
            "rib_stress_MPa": round(sigma_MPa, 3),
            "yield_SF": round(yield_SF, 2),
            "buckling_SF": round(buckling_SF, 2),
        })
    print()

    # === Effective core shear ===
    # Wheel under radial load F sees shear V flowing through the rim
    # cross-section. For a screening-level estimate of average core
    # shear stress: tau ~ F / (h_core * b)
    avg_core_shear_MPa = max_load_N / (CORE_HEIGHT_M * WHEEL_WIDTH_M) / 1e6
    # Effective shear modulus of the lattice (rough rule-of-mixtures
    # for a ±theta lattice; full anisotropic homogenization would be
    # more accurate).
    G_eff_factor = (
        LATTICE_VOLUME_FRACTION
        * (math.sin(HELIX_ANGLE_RAD) * math.cos(HELIX_ANGLE_RAD)) ** 2
        * 4.0  # factor of 4 from rule-of-mixtures derivation for ±theta
    )
    G_lattice_effective_Pa = G_PEKK_CNT_CF_PA * G_eff_factor
    # Effective lattice shear strength: ribs yield when their axial
    # stress reaches sigma_yield. Project to shear.
    tau_lattice_allow_MPa = (
        SIGMA_YIELD_MPa
        * LATTICE_VOLUME_FRACTION
        * math.sin(HELIX_ANGLE_RAD)
        * math.cos(HELIX_ANGLE_RAD)
    )
    print("Effective core shear (sandwich-core analogy):")
    print(f"  Avg core shear at max load (F / h_c·b):  "
          f"{avg_core_shear_MPa:.3f} MPa")
    print(f"  Effective lattice shear modulus:         "
          f"{G_lattice_effective_Pa/1e6:.0f} MPa")
    print(f"  Effective lattice shear allowable:       "
          f"{tau_lattice_allow_MPa:.1f} MPa")
    print(f"  Lattice shear SF:                        "
          f"{tau_lattice_allow_MPa/avg_core_shear_MPa:.0f}")
    print()
    print("  (Typical aerospace honeycomb: G_eff 50-300 MPa, "
          "tau_allow 0.5-3 MPa)")
    print()

    # === Sensitivity sweep on contact patch size ===
    print("Sensitivity sweep on contact patch length (load distribution):")
    print(f"{'Patch (mm)':>12}  {'n_ribs':>8}  "
          f"{'load/rib (max F)':>17}  {'stress (MPa)':>13}  "
          f"{'yield SF':>10}  {'buckling SF':>12}")
    print("-" * 80)
    patch_lengths_mm = [5, 10, 20, 30, 50, 75, 100, 150]
    sens_rows = []
    for patch_mm in patch_lengths_mm:
        n_r = ribs_in_contact_patch(patch_mm, NOMINAL_PATCH_AXIAL_MM)
        load_per_rib = per_rib_axial_load_N(max_load_N, n_r)
        sigma_MPa = load_per_rib / (RIB_CROSS_AREA_M2 * 1e6)
        yield_SF = SIGMA_YIELD_MPa / sigma_MPa if sigma_MPa > 0 else float("inf")
        buck_SF = (
            buck["critical_load_N"] / load_per_rib
            if load_per_rib > 0 else float("inf")
        )
        print(f"{patch_mm:>12}  {n_r:>8}  {load_per_rib:>15.1f} N  "
              f"{sigma_MPa:>13.3f}  {yield_SF:>10.2f}  {buck_SF:>12.1f}")
        sens_rows.append({
            "patch_length_mm": patch_mm,
            "n_ribs_in_patch": n_r,
            "load_per_rib_N": round(load_per_rib, 3),
            "rib_stress_MPa": round(sigma_MPa, 4),
            "yield_SF": round(yield_SF, 3),
            "buckling_SF": round(buck_SF, 3),
        })
    print()

    # === Plot: per-rib stress vs contact patch length ===
    fig, ax = plt.subplots(figsize=(9, 5.5))
    patch_grid = np.linspace(5, 200, 80)
    sigmas, yield_sfs = [], []
    for p in patch_grid:
        nr = ribs_in_contact_patch(p, NOMINAL_PATCH_AXIAL_MM)
        lpr = per_rib_axial_load_N(max_load_N, nr)
        sig = lpr / (RIB_CROSS_AREA_M2 * 1e6)
        sigmas.append(sig)
        yield_sfs.append(SIGMA_YIELD_MPa / sig if sig > 0 else float("inf"))
    ax2 = ax.twinx()
    ax.plot(patch_grid, sigmas, color="steelblue", linewidth=2,
            label="Rib stress (max load)")
    ax2.plot(patch_grid, yield_sfs, color="darkorange", linewidth=2,
             linestyle="--", label="Yield SF")
    ax.axhline(SIGMA_YIELD_MPa, color="red", linestyle=":", alpha=0.6,
               label=f"σ_yield ({SIGMA_YIELD_MPa:.0f} MPa)")
    ax.axhline(buck["critical_stress_MPa"], color="purple",
               linestyle=":", alpha=0.6,
               label=f"σ_cr buckling "
                     f"({buck['critical_stress_MPa']:.0f} MPa)")
    ax.set_xlabel("Contact patch length, circumferential (mm)")
    ax.set_ylabel("Per-rib stress at max wheel load (MPa)")
    ax2.set_ylabel("Yield safety factor")
    ax.set_yscale("log")
    ax2.set_yscale("log")
    ax.set_title("AURORA-Mono — rib lattice stress vs contact patch size\n"
                 "(uniform rib-load sharing assumption)")
    ax.grid(True, linestyle="--", alpha=0.4)
    # Combine legends
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=9, loc="best")
    fig.tight_layout()
    fig.savefig("plots/rib_lattice_sensitivity.png", dpi=120)
    print("Wrote plots/rib_lattice_sensitivity.png")

    # === CSV outputs ===
    summary_row = {
        "lattice_circumference_mm": round(LATTICE_MEAN_CIRC_M * 1000, 2),
        "lattice_width_mm": round(WHEEL_WIDTH_M * 1000, 2),
        "core_height_mm": round(CORE_HEIGHT_M * 1000, 2),
        "n_ribs_total": N_RIBS_TOTAL,
        "helix_angle_deg": HELIX_ANGLE_DEG,
        "rib_web_thickness_mm": round(RIB_WEB_THICKNESS_M * 1000, 2),
        "rib_cross_section_mm2": round(RIB_CROSS_AREA_M2 * 1e6, 3),
        "lattice_volume_fraction_pct": round(LATTICE_VOLUME_FRACTION * 100, 2),
        "rib_slenderness_ratio": round(buck["slenderness_ratio"], 3),
        "rib_buckling_regime": buck["regime"],
        "rib_critical_stress_MPa": round(buck["critical_stress_MPa"], 2),
        "rib_critical_load_N": round(buck["critical_load_N"], 1),
        "G_lattice_effective_MPa": round(G_lattice_effective_Pa / 1e6, 1),
        "lattice_shear_allowable_MPa": round(tau_lattice_allow_MPa, 2),
        "avg_core_shear_max_load_MPa": round(avg_core_shear_MPa, 4),
        "lattice_shear_SF": round(
            tau_lattice_allow_MPa / avg_core_shear_MPa, 1
        ),
    }
    pd.DataFrame([summary_row]).to_csv(
        "rib_lattice_check_summary.csv", index=False
    )
    pd.DataFrame(case_rows).to_csv(
        "rib_lattice_check_cases.csv", index=False
    )
    pd.DataFrame(sens_rows).to_csv(
        "rib_lattice_check_sensitivity.csv", index=False
    )
    print("Wrote rib_lattice_check_summary.csv")
    print("Wrote rib_lattice_check_cases.csv")
    print("Wrote rib_lattice_check_sensitivity.csv")
    print()

    # === Verdict ===
    print("=" * 64)
    print("VERDICT")
    print("=" * 64)
    worst_case = case_rows[-1]  # 1 rib bears all the load
    nominal_case = case_rows[1]  # max load, nominal patch
    if (worst_case["yield_SF"] >= 2.0
            and worst_case["buckling_SF"] >= 2.0):
        verdict = (
            "Lattice has substantial margin in all checked load cases, "
            "including the worst conceivable load concentration "
            "(single rib bearing the full rock-event load)."
        )
    elif (nominal_case["yield_SF"] >= 2.0
          and nominal_case["buckling_SF"] >= 2.0):
        verdict = (
            "Lattice has comfortable margin under uniform load sharing, "
            "but margin tightens under adverse load concentration."
        )
    else:
        verdict = (
            "Lattice margin is tight; review load distribution assumptions "
            "and consider rib geometry changes."
        )
    print(verdict)
    print()
    print("Lattice volume fraction "
          f"({LATTICE_VOLUME_FRACTION*100:.1f}%) sits well above typical")
    print("aerospace honeycomb (1-5%), reflecting a more robust core than is")
    print("strictly needed for the wheel loads; this trades mass for")
    print("structural redundancy and damage tolerance.")
    print()
    print("This screening uses a uniform-load-sharing assumption with a")
    print("conservative reduction to one-rib-bears-all in the worst case.")
    print("A 3D truss FEM of the lattice with the actual contact-patch")
    print("pressure distribution would give the real per-rib stresses.")


if __name__ == "__main__":
    main()
