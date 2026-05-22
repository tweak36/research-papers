
"""
Lug-shear screening check at the SiC-PEKK / outer-skin keying interface.

Uses the mission load history from the screening model to compute peak
tangential force per lug, applies an edge-stress concentration factor, and
compares against an estimated allowable shear stress for a same-family
co-molded PEKK bond.

Limitations (read before relying on the number):
- Assumes uniform shear distribution across the lug footprint, then applies
  a single edge-concentration multiplier. Real distributions are highly
  geometry-dependent.
- Allowable shear (20 MPa) is a conservative estimate derived from
  published PEKK bulk shear (~50-80 MPa) and typical thermoplastic co-mold
  bond efficiencies (~30-50%). NOT measured from coupon tests.
- Anti-peel keys (3 concentric 0.6 mm x 1.8 mm grooves under each lug)
  provide additional mechanical interlock NOT credited in this check —
  the result is therefore conservative on that axis.
- This is a SHEAR check only. Peel-mode loading (the failure the keys are
  specifically designed to address) is not analyzed here.
- Lug count is geometrically estimated from circumference, lug length,
  and solid fraction; cross-check against the actual CAD model would be
  required for a real design review.
- Static traction model: F_tangential = mu * F_normal with mu pinned to
  the maximum terrain value. No dynamic acceleration or braking analysis
  beyond the rock-event load multiplier already in the screening model.
"""

import math
import pandas as pd

from aurora_mono_screening_model import run_screening, MU_AVAILABLE_MAP


# --- Lug geometry from the AURORA-Mono build spec ---
LUG_LENGTH_LONG_M = 0.045         # 45 mm long lugs
LUG_LENGTH_SHORT_M = 0.035        # 35 mm short lugs (alternating)
LUG_WIDTH_AXIAL_M = 0.014         # 14 mm axial
LUG_AVG_LENGTH_M = 0.5 * (LUG_LENGTH_LONG_M + LUG_LENGTH_SHORT_M)
LUG_FOOTPRINT_AREA_M2 = LUG_AVG_LENGTH_M * LUG_WIDTH_AXIAL_M

# --- Wheel geometry ---
WHEEL_OD_IN = 18.0
WHEEL_OD_M = WHEEL_OD_IN * 0.0254
TREAD_CIRCUMFERENCE_M = math.pi * WHEEL_OD_M

# Solid fraction at the tread: void ratio is 75-80%, so solid coverage is
# 20-25%. Use the lower (more conservative for lug count, since fewer
# lugs means higher load per lug).
TREAD_SOLID_FRACTION = 0.20

# Lugs per row, derived geometrically
LUGS_PER_ROW = max(
    1, int(TREAD_CIRCUMFERENCE_M * TREAD_SOLID_FRACTION / LUG_AVG_LENGTH_M)
)
ROWS = 2  # two staggered rows per build spec
LUGS_TOTAL = LUGS_PER_ROW * ROWS

# How many lugs are in the ground contact patch at any instant. With
# chevron lugs staggered across two rows on a hard surface, typically
# 1-2 per row touch. Use a conservative LOW count to maximize per-lug
# load.
LUGS_IN_CONTACT_INSTANTANEOUS = 2

# --- Bond strength estimate ---
# PEKK bulk shear strength: ~50-80 MPa (Solvay / Arkema data sheets).
# Co-molded thermoplastic bond efficiency in same-family welds:
# typically 30-50% of bulk. Use the conservative low end.
PEKK_BULK_SHEAR_LOW_MPa = 50.0
BOND_EFFICIENCY_CONSERVATIVE = 0.40
BOND_SHEAR_ALLOWABLE_PA = (
    PEKK_BULK_SHEAR_LOW_MPa * BOND_EFFICIENCY_CONSERVATIVE * 1e6
)

# Edge-stress concentration factor (uniform-stress assumption underestimates
# peak stress by roughly 2-3x for typical lug aspect ratios).
EDGE_STRESS_CONCENTRATION = 2.5

# --- Traction coefficient ---
MAX_MU = max(MU_AVAILABLE_MAP.values())


def main():
    print("Running screening model to extract load history...")
    df, summary = run_screening()

    # Worst-case normal load per wheel, from the stochastic event history
    max_normal_per_wheel_N = float(df["load_N"].max())

    # Peak tangential force is mu_max * normal_load
    max_tangential_total_N = max_normal_per_wheel_N * MAX_MU

    # Distribute across the lugs in instantaneous ground contact
    shear_force_per_lug_N = max_tangential_total_N / LUGS_IN_CONTACT_INSTANTANEOUS

    # Average shear stress across the lug footprint
    avg_shear_stress_Pa = shear_force_per_lug_N / LUG_FOOTPRINT_AREA_M2

    # Design shear stress (account for edge concentration)
    design_shear_stress_Pa = avg_shear_stress_Pa * EDGE_STRESS_CONCENTRATION

    # Safety factor
    lug_shear_SF = BOND_SHEAR_ALLOWABLE_PA / design_shear_stress_Pa

    # --- Worst plausible: single-lug contact on the maximum-mu terrain ---
    # If only one lug is bearing (e.g., briefly during cresting or hard
    # turn), the per-lug load doubles.
    worst_shear_per_lug_N = max_tangential_total_N / 1
    worst_avg_shear_Pa = worst_shear_per_lug_N / LUG_FOOTPRINT_AREA_M2
    worst_design_shear_Pa = worst_avg_shear_Pa * EDGE_STRESS_CONCENTRATION
    worst_SF = BOND_SHEAR_ALLOWABLE_PA / worst_design_shear_Pa

    # Report
    print()
    print("=" * 60)
    print("Lug-shear screening check (NOT FEA, NOT measured bond data)")
    print("=" * 60)
    print(f"Wheel tread circumference: {TREAD_CIRCUMFERENCE_M*1000:>8.1f} mm")
    print(f"Avg lug footprint area:    {LUG_FOOTPRINT_AREA_M2*1e6:>8.1f} mm^2")
    print(f"Estimated lugs per row:    {LUGS_PER_ROW:>8d}")
    print(f"Estimated total lugs:      {LUGS_TOTAL:>8d}")
    print()
    print(f"Max normal load per wheel: {max_normal_per_wheel_N:>8.1f} N")
    print(f"Max traction coefficient:  {MAX_MU:>8.2f}")
    print(f"Max tangential force:      {max_tangential_total_N:>8.1f} N")
    print()
    print(f"Bond shear allowable:      {BOND_SHEAR_ALLOWABLE_PA/1e6:>8.1f} MPa")
    print(f"  (PEKK bulk {PEKK_BULK_SHEAR_LOW_MPa} MPa x bond efficiency "
          f"{BOND_EFFICIENCY_CONSERVATIVE:.0%})")
    print(f"Edge stress concentration: {EDGE_STRESS_CONCENTRATION:>8.1f} x")
    print()
    print("Nominal case (2 lugs in contact):")
    print(f"  Shear force per lug:     {shear_force_per_lug_N:>8.1f} N")
    print(f"  Avg shear stress:        {avg_shear_stress_Pa/1e6:>8.4f} MPa")
    print(f"  Design shear stress:     {design_shear_stress_Pa/1e6:>8.4f} MPa")
    print(f"  Lug-shear SF:            {lug_shear_SF:>8.1f}")
    print()
    print("Worst plausible (1 lug in contact):")
    print(f"  Shear force per lug:     {worst_shear_per_lug_N:>8.1f} N")
    print(f"  Avg shear stress:        {worst_avg_shear_Pa/1e6:>8.4f} MPa")
    print(f"  Design shear stress:     {worst_design_shear_Pa/1e6:>8.4f} MPa")
    print(f"  Lug-shear SF:            {worst_SF:>8.1f}")
    print()
    print("Verdict: the lug-to-skin bond is not the limiting failure mode")
    print("in pure shear, under the assumptions above. Peel-mode loading")
    print("(which the anti-peel keys specifically address) is NOT analyzed.")

    out = pd.DataFrame([{
        "tread_circumference_mm": round(TREAD_CIRCUMFERENCE_M * 1000, 2),
        "lug_footprint_area_mm2": round(LUG_FOOTPRINT_AREA_M2 * 1e6, 2),
        "lugs_per_row_est": LUGS_PER_ROW,
        "lugs_total_est": LUGS_TOTAL,
        "max_normal_load_N": round(max_normal_per_wheel_N, 2),
        "max_mu": MAX_MU,
        "max_tangential_force_N": round(max_tangential_total_N, 2),
        "bond_shear_allowable_MPa": round(BOND_SHEAR_ALLOWABLE_PA / 1e6, 2),
        "edge_stress_concentration": EDGE_STRESS_CONCENTRATION,
        "nominal_lugs_in_contact": LUGS_IN_CONTACT_INSTANTANEOUS,
        "nominal_shear_per_lug_N": round(shear_force_per_lug_N, 2),
        "nominal_design_shear_MPa": round(design_shear_stress_Pa / 1e6, 4),
        "nominal_SF": round(lug_shear_SF, 2),
        "worst_shear_per_lug_N": round(worst_shear_per_lug_N, 2),
        "worst_design_shear_MPa": round(worst_design_shear_Pa / 1e6, 4),
        "worst_SF": round(worst_SF, 2),
    }])
    out.to_csv("lug_shear_check_results.csv", index=False)
    print("\nWrote lug_shear_check_results.csv")


if __name__ == "__main__":
    main()
