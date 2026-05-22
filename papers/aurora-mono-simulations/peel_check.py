
"""
Peel-mode screening check at the SiC-PEKK / outer-skin co-molded bond.

Peel is fundamentally different from shear. The relevant failure mode is a
crack propagating along the lug-to-skin interface, driven by stress
concentrating at the bond edge. The dominant on-Moon load case that
produces this is eccentric vertical loading: when the wheel crests a rock,
the contact patch shifts to one edge of the lug, putting that lug under a
bending moment that tries to lift its trailing edge.

Model (first-order, screening-level):
- Treat each lug as a rigid rectangular pad bonded to the skin.
- Apply the per-lug normal load at a horizontal offset `e` from the lug
  centerline. Worst case: e = L/2 (load at the leading edge).
- Compute the resulting bending moment M = F * e.
- Linear-stress-distribution assumption across the bond area gives a
  peak peel stress at the trailing edge:
      sigma_peel_peak = 6 * M / (b * L^2)
  where b is lug width (axial), L is lug length (circumferential).
- Compare against an effective allowable that combines the chemical bond
  strength with a multiplier crediting the mechanical anti-peel keys.

Limitations (read before relying on the SF):
- Pure stress-based; no fracture-mechanics (G_c / K_IC) analysis.
- Linear stress distribution under the lug is an approximation. Real
  distribution depends on lug stiffness, skin compliance, and contact
  mechanics; an FEM beam-on-elastic-foundation analysis would refine it.
- Bond chemical allowable (5 MPa) is conservative for thermoplastic same-
  family co-mold; not measured for THIS bond.
- Anti-peel key multiplier (2.0x) is an engineering estimate based on
  mechanical-interlock practice; it is NOT derived from the actual key
  geometry (3 grooves x 0.6 mm deep x 1.8 mm wide). A coupon pull test
  would replace this assumption.
- No thermal-cycling stress. Differential CTE between SiC-PEKK and
  PEKK-CNT/CF would create cyclic peel forces over the lunar diurnal
  cycle; not modeled here.
- No cycle-by-cycle fatigue accumulator on the bond.
- Eccentric-load offset is taken at its geometric extreme (L/2). Real
  cresting dynamics depend on rock size, wheel velocity, and suspension
  response.
"""

import math
import pandas as pd

from aurora_mono_screening_model import run_screening, MU_AVAILABLE_MAP


# --- Lug geometry from the AURORA-Mono build spec ---
LUG_LENGTH_LONG_M = 0.045
LUG_LENGTH_SHORT_M = 0.035
LUG_WIDTH_AXIAL_M = 0.014
LUG_AVG_LENGTH_M = 0.5 * (LUG_LENGTH_LONG_M + LUG_LENGTH_SHORT_M)
LUG_FOOTPRINT_AREA_M2 = LUG_AVG_LENGTH_M * LUG_WIDTH_AXIAL_M

# --- Contact distribution ---
LUGS_IN_CONTACT_INSTANTANEOUS = 2  # conservative

# --- Bond allowable (peel / tensile) ---
# Conservative thermoplastic co-mold same-family allowable. Real measured
# values for PEKK-PEKK welds with surface preparation typically run 5-15 MPa.
BOND_CHEMICAL_TENSILE_ALLOWABLE_PA = 5.0e6

# Multiplier crediting the mechanical anti-peel keys (3 grooves under each
# lug). Conservative; an FEM or coupon test would set this directly.
ANTI_PEEL_KEY_MULTIPLIER = 2.0

EFFECTIVE_PEEL_ALLOWABLE_PA = (
    BOND_CHEMICAL_TENSILE_ALLOWABLE_PA * ANTI_PEEL_KEY_MULTIPLIER
)


def peak_peel_stress_Pa(load_N, eccentric_offset_m, lug_width_m, lug_length_m):
    """Peak peel stress at the bond edge under offset normal load.

    Assumes a rigid rectangular pad on a uniform bond, linear stress
    distribution across the bond area in the direction of the offset.
    """
    moment_Nm = load_N * eccentric_offset_m
    # Section modulus of the bond rectangle bending about the lug centerline,
    # taking the lug length as the span:
    #   sigma_peak = 6 * M / (b * L^2)
    sigma_pa = 6.0 * moment_Nm / (lug_width_m * lug_length_m ** 2)
    return sigma_pa


def peel_SF(load_N, offset_m, allowable_Pa,
            lug_width_m=LUG_WIDTH_AXIAL_M, lug_length_m=LUG_AVG_LENGTH_M):
    sigma = peak_peel_stress_Pa(load_N, offset_m, lug_width_m, lug_length_m)
    if sigma <= 0:
        return float("inf"), sigma
    return allowable_Pa / sigma, sigma


def main():
    print("Running screening model to extract load history...")
    df, summary = run_screening()
    max_normal_per_wheel_N = float(df["load_N"].max())
    static_load_per_wheel_N = float(summary["static_load_per_wheel_N"])

    # Per-lug normal loads (worst rock event + nominal cruise)
    worst_per_lug_N = max_normal_per_wheel_N / LUGS_IN_CONTACT_INSTANTANEOUS
    cruise_per_lug_N = static_load_per_wheel_N / LUGS_IN_CONTACT_INSTANTANEOUS

    # Eccentric offsets
    edge_offset_m = LUG_AVG_LENGTH_M / 2.0   # load at lug edge (worst)
    moderate_offset_m = LUG_AVG_LENGTH_M / 4.0  # load 25% off-center

    cases = [
        ("Cruise, centered (e = 0)",
         cruise_per_lug_N, 0.0),
        ("Cruise, moderate eccentricity (e = L/4)",
         cruise_per_lug_N, moderate_offset_m),
        ("Cruise, worst eccentricity (e = L/2)",
         cruise_per_lug_N, edge_offset_m),
        ("Worst rock event, moderate eccentricity (e = L/4)",
         worst_per_lug_N, moderate_offset_m),
        ("Worst rock event, worst eccentricity (e = L/2)",
         worst_per_lug_N, edge_offset_m),
    ]

    print()
    print("=" * 64)
    print("Peel-mode screening check (NOT fracture mechanics, NOT FEA)")
    print("=" * 64)
    print(f"Lug footprint:           {LUG_AVG_LENGTH_M*1000:>5.1f} x "
          f"{LUG_WIDTH_AXIAL_M*1000:.1f} mm "
          f"({LUG_FOOTPRINT_AREA_M2*1e6:.0f} mm^2)")
    print(f"Lugs in contact:         {LUGS_IN_CONTACT_INSTANTANEOUS}")
    print(f"Static load / wheel:     {static_load_per_wheel_N:>5.1f} N "
          f"(=> {cruise_per_lug_N:.1f} N per lug)")
    print(f"Max load / wheel:        {max_normal_per_wheel_N:>5.1f} N "
          f"(=> {worst_per_lug_N:.1f} N per lug)")
    print()
    print(f"Chemical bond allowable: {BOND_CHEMICAL_TENSILE_ALLOWABLE_PA/1e6:>5.1f} MPa")
    print(f"Anti-peel key multiplier:{ANTI_PEEL_KEY_MULTIPLIER:>5.1f} x")
    print(f"Effective allowable:     {EFFECTIVE_PEEL_ALLOWABLE_PA/1e6:>5.1f} MPa")
    print()
    print(f"{'Case':<48} {'Peak stress':>12}  {'SF':>6}")
    print("-" * 70)

    results = []
    for label, load_N, offset_m in cases:
        sf, sigma = peel_SF(load_N, offset_m, EFFECTIVE_PEEL_ALLOWABLE_PA)
        sf_str = f"{sf:.1f}" if sf < 1e4 else "inf"
        sig_str = f"{sigma/1e6:.3f} MPa" if sigma > 0 else "0.000 MPa"
        print(f"{label:<48} {sig_str:>12}  {sf_str:>6}")
        results.append({
            "case": label,
            "load_per_lug_N": round(load_N, 2),
            "eccentric_offset_mm": round(offset_m * 1000, 2),
            "peak_peel_stress_MPa": round(sigma / 1e6, 4),
            "effective_allowable_MPa": round(EFFECTIVE_PEEL_ALLOWABLE_PA / 1e6, 2),
            "peel_SF": (round(sf, 2) if sf < 1e4 else None),
        })
    print()

    # --- Sensitivity on the two most uncertain inputs ---
    print("Sensitivity sweep on worst-case (rock event + worst eccentricity):")
    print(f"{'Chem allowable':>16}  {'Key mult':>10}  "
          f"{'Effective':>10}  {'Peak stress':>12}  {'SF':>6}")
    print("-" * 64)
    sensitivity_results = []
    chem_levels_MPa = [3.0, 5.0, 7.0, 10.0, 15.0]
    key_mults = [1.0, 2.0, 3.0]
    for chem_MPa in chem_levels_MPa:
        for km in key_mults:
            eff = chem_MPa * km * 1e6
            sf, sigma = peel_SF(worst_per_lug_N, edge_offset_m, eff)
            sf_str = f"{sf:.1f}" if sf < 1e4 else "inf"
            print(f"{chem_MPa:>14.1f}MPa  {km:>10.1f}x  "
                  f"{chem_MPa*km:>9.1f}MPa  {sigma/1e6:>9.3f}MPa  {sf_str:>6}")
            sensitivity_results.append({
                "chemical_allowable_MPa": chem_MPa,
                "key_multiplier": km,
                "effective_allowable_MPa": chem_MPa * km,
                "peak_peel_stress_MPa": round(sigma / 1e6, 4),
                "peel_SF": round(sf, 2),
            })
    print()

    # --- Verdict block ---
    worst_case_sf = next(
        r["peel_SF"] for r in results
        if "Worst rock event" in r["case"]
        and r["eccentric_offset_mm"] == round(edge_offset_m * 1000, 2)
    )
    if worst_case_sf is None or worst_case_sf >= 2.0:
        verdict = (
            "Adequate peel margin under nominal assumptions. SF >= 2 at the "
            "worst rock event with worst eccentricity."
        )
    elif worst_case_sf >= 1.0:
        verdict = (
            "Marginal peel margin under nominal assumptions. SF >= 1 but "
            "below the typical 2x screening threshold."
        )
    else:
        verdict = (
            "INSUFFICIENT peel margin under nominal assumptions. Worst rock "
            "event with worst eccentricity predicts bond debond. Design "
            "iteration required."
        )
    print(f"Verdict: {verdict}")
    print()
    print("This is a SCREENING check. A fracture-mechanics analysis using "
          "G_c (critical strain energy release rate) for the actual co-mold "
          "bond would be the correct next-fidelity step.")

    # --- CSV outputs ---
    pd.DataFrame(results).to_csv("peel_check_results.csv", index=False)
    pd.DataFrame(sensitivity_results).to_csv(
        "peel_check_sensitivity.csv", index=False
    )
    print()
    print("Wrote peel_check_results.csv")
    print("Wrote peel_check_sensitivity.csv")


if __name__ == "__main__":
    main()
