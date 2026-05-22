
"""
Thermal-cycling stress check at the SiC-PEKK / PEKK-CNT/CF bond from
differential CTE under the lunar diurnal temperature swing.

When the wheel sits on the lunar surface, the bonded interface between
the SiC-PEKK tread and the PEKK-CNT/CF outer skin sees cyclic stress
from the two materials wanting to expand by different amounts:

    sigma_constrained = E_tread * (alpha_tread - alpha_skin) * delta_T

This is the constrained-strain upper bound on stress at the interface,
treating one material as rigidly held by the other and ignoring through-
thickness compliance and viscoelastic relaxation. Real peak peel stress
at the lug edges is some fraction of this bound; we report a band by
sweeping a "peel recovery factor" from 0.3 (heavily relaxed) to 1.0
(no relaxation).

Diurnal cycle:
  Lunar surface temperature swings from about -173 C (night) to
  +127 C (day), giving delta_T = 300 K per full cycle.
  One lunar day is 29.5 Earth days, so ~12.4 thermal cycles per year.

Material properties (ESTIMATED, not measured for the actual formulations):
  Tread SiC-PEKK:    E = 5 GPa,  alpha = 29 ppm/K
    (30% vol SiC at 4 ppm/K, 70% PEKK at ~40 ppm/K, rule of mixtures)
  Skin PEKK-CNT/CF:  E = 50 GPa, alpha = 10 ppm/K
    (CF-dominated in-plane CTE for CNT/CF-reinforced PEKK)
  Differential alpha = 19 ppm/K (nominal)

Bond allowables (from peel_check.py):
  Chemical bond:      5 MPa
  Anti-peel key x:    2.0
  Effective static:  10 MPa
  Endurance ratio:    0.25  ->  endurance limit 2.5 MPa

Limitations (read before relying on the numbers):
- Closed-form constrained-strain bound; an FEM analysis with the actual
  3D geometry would resolve edge stresses properly.
- NO viscoelastic / creep relaxation modeled. PEKK creeps significantly
  near its Tg (~165 C); long lunar-day dwells at +127 C would relax a
  meaningful fraction of the peak stress. The numbers here are
  CONSERVATIVE on that axis.
- NO transient thermal conduction; assumes the bond reaches both
  extremes instantaneously.
- CTE values are bulk / rule-of-mixtures estimates. A coupon test on
  the actual SiC-PEKK and PEKK-CNT/CF formulations would replace them.
- Each diurnal cycle treated as one full stress reversal; partial-cycle
  events (eclipses, terminator crossings) not counted.
- No mean-stress effect on the S-N curve (no Goodman correction).
"""

import math
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


# --- Material properties (estimated, not measured) ---
E_TREAD_PA = 5.0e9       # SiC-PEKK
E_SKIN_PA = 50.0e9       # PEKK-CNT/CF
ALPHA_TREAD = 29.0e-6    # SiC-PEKK, K^-1
ALPHA_SKIN = 10.0e-6     # PEKK-CNT/CF, K^-1
DELTA_ALPHA = ALPHA_TREAD - ALPHA_SKIN  # 19e-6 K^-1

# --- Lunar diurnal cycle ---
T_MAX_C = 127.0
T_MIN_C = -173.0
DELTA_T_FULL_K = T_MAX_C - T_MIN_C   # 300 K full swing
DELTA_T_HALF_K = DELTA_T_FULL_K / 2  # 150 K half swing
LUNAR_DAY_DAYS = 29.5
CYCLES_PER_YEAR = 365.25 / LUNAR_DAY_DAYS  # ~12.4

# --- Edge stress fraction ---
# Peak peel at the lug edge from a constrained-thermal interior shear is
# typically 30-50% of the interior shear in practice (compliance +
# viscoelastic relaxation). 1.0 = no relaxation, fully constrained.
PEEL_RECOVERY_NOMINAL = 0.40

# --- Bond allowables (matching peel_check.py / fatigue_check.py) ---
BOND_CHEMICAL_MPa = 5.0
ANTI_PEEL_KEY_MULTIPLIER = 2.0
BOND_EFFECTIVE_PEEL_MPa = BOND_CHEMICAL_MPa * ANTI_PEEL_KEY_MULTIPLIER
BOND_ENDURANCE_RATIO = 0.25
BOND_ENDURANCE_LIMIT_MPa = BOND_EFFECTIVE_PEEL_MPa * BOND_ENDURANCE_RATIO


def constrained_thermal_stress_MPa(E_Pa, delta_alpha, delta_T_K):
    """Upper bound interior shear / tensile stress from constrained
    differential thermal expansion."""
    return E_Pa * delta_alpha * delta_T_K / 1e6


def basquin_sn_calibrate(sigma_static_MPa, endurance_ratio, endurance_cycles=1e6):
    sigma_endurance = sigma_static_MPa * endurance_ratio
    b = math.log10(endurance_cycles) / (sigma_static_MPa - sigma_endurance)
    a = b * sigma_static_MPa
    return a, b


def cycles_to_failure(sigma_MPa, a, b, endurance_limit_MPa):
    """N_f from log-linear Basquin; infinite below endurance, <1 above
    static (instantaneous failure)."""
    if sigma_MPa < endurance_limit_MPa:
        return float("inf")
    log_N = a - b * sigma_MPa
    if log_N < 0:
        return 0.5
    return 10 ** log_N


def fmt_life(life_years):
    if math.isinf(life_years):
        return "infinite"
    if life_years >= 1.0:
        return f"{life_years:.1f} years"
    if life_years >= 1.0 / 365.25:
        return f"{life_years * 365.25:.1f} days"
    if life_years >= 1.0 / (365.25 * 24):
        return f"{life_years * 365.25 * 24:.1f} hours"
    return f"{life_years * CYCLES_PER_YEAR:.2f} cycles"


def main():
    os.makedirs("plots", exist_ok=True)

    print("=" * 64)
    print("Thermal-cycling stress check (CTE mismatch, lunar diurnal)")
    print("=" * 64)
    print(f"Tread SiC-PEKK:    E={E_TREAD_PA/1e9:.0f} GPa, "
          f"alpha={ALPHA_TREAD*1e6:.1f} ppm/K")
    print(f"Skin PEKK-CNT/CF:  E={E_SKIN_PA/1e9:.0f} GPa, "
          f"alpha={ALPHA_SKIN*1e6:.1f} ppm/K")
    print(f"Delta-alpha:       {DELTA_ALPHA*1e6:.1f} ppm/K")
    print(f"Diurnal swing:     {T_MIN_C:.0f} -> {T_MAX_C:.0f} C, "
          f"delta-T = {DELTA_T_FULL_K:.0f} K")
    print(f"Cycles per year:   {CYCLES_PER_YEAR:.2f}")
    print()
    print(f"Bond effective allowable:  {BOND_EFFECTIVE_PEEL_MPa:.1f} MPa "
          f"({BOND_CHEMICAL_MPa} chem x {ANTI_PEEL_KEY_MULTIPLIER}x keys)")
    print(f"Bond endurance limit:      {BOND_ENDURANCE_LIMIT_MPa:.2f} MPa "
          f"(R_e = {BOND_ENDURANCE_RATIO})")
    print()

    # --- Single-cycle stress (static check) ---
    sigma_interior_full = constrained_thermal_stress_MPa(
        E_TREAD_PA, DELTA_ALPHA, DELTA_T_FULL_K
    )
    sigma_interior_half = constrained_thermal_stress_MPa(
        E_TREAD_PA, DELTA_ALPHA, DELTA_T_HALF_K
    )
    sigma_peel_full = sigma_interior_full * PEEL_RECOVERY_NOMINAL
    sigma_peel_half = sigma_interior_half * PEEL_RECOVERY_NOMINAL

    sf_interior_full = BOND_EFFECTIVE_PEEL_MPa / sigma_interior_full
    sf_peel_full = BOND_EFFECTIVE_PEEL_MPa / sigma_peel_full
    sf_peel_half = BOND_EFFECTIVE_PEEL_MPa / sigma_peel_half

    print("Single-cycle stress (no fatigue, no relaxation modelled):")
    print(f"  Interior constrained (full 300 K cycle):  "
          f"{sigma_interior_full:>6.1f} MPa   SF = {sf_interior_full:>4.2f}")
    print(f"  Interior constrained (half 150 K cycle):  "
          f"{sigma_interior_half:>6.1f} MPa   "
          f"SF = {BOND_EFFECTIVE_PEEL_MPa/sigma_interior_half:>4.2f}")
    print(f"  Peak peel at edge (x{PEEL_RECOVERY_NOMINAL:.1f} factor, "
          f"full cycle):  {sigma_peel_full:>6.1f} MPa   "
          f"SF = {sf_peel_full:>4.2f}")
    print(f"  Peak peel at edge (x{PEEL_RECOVERY_NOMINAL:.1f} factor, "
          f"half cycle):  {sigma_peel_half:>6.1f} MPa   "
          f"SF = {sf_peel_half:>4.2f}")
    print()

    # --- Fatigue accumulation across mission life ---
    a, b = basquin_sn_calibrate(BOND_EFFECTIVE_PEEL_MPa, BOND_ENDURANCE_RATIO)
    N_f = cycles_to_failure(sigma_peel_full, a, b, BOND_ENDURANCE_LIMIT_MPa)
    life_years = (N_f / CYCLES_PER_YEAR) if math.isfinite(N_f) else float("inf")

    print("Miner's-rule fatigue (using nominal edge peel from full cycle):")
    print(f"  Stress per cycle:        {sigma_peel_full:.2f} MPa")
    print(f"  Endurance limit:         {BOND_ENDURANCE_LIMIT_MPa:.2f} MPa")
    if math.isinf(N_f):
        print(f"  Cycles to failure:       infinite (below endurance)")
        print(f"  Fatigue life:            infinite")
    else:
        print(f"  Cycles to failure:       {N_f:.2g}")
        print(f"  Fatigue life:            {fmt_life(life_years)}")
    print()

    # --- Sensitivity sweep on the two most uncertain inputs ---
    print("Sensitivity sweep (delta-alpha and peel recovery factor):")
    print(f"{'d-alpha':>10}  {'recovery':>10}  {'sigma_peel':>12}  "
          f"{'SF (static)':>12}  {'cycles N_f':>12}  {'life':>14}")
    print("-" * 80)
    sens_rows = []
    d_alpha_levels_ppm = [10, 15, 19, 25, 30]  # ppm/K
    recovery_levels = [0.30, 0.40, 0.50, 0.70, 1.00]
    for d_alpha_ppm in d_alpha_levels_ppm:
        for rec in recovery_levels:
            d_a = d_alpha_ppm * 1e-6
            sig_int = constrained_thermal_stress_MPa(
                E_TREAD_PA, d_a, DELTA_T_FULL_K
            )
            sig_p = sig_int * rec
            sf = BOND_EFFECTIVE_PEEL_MPa / sig_p
            nf = cycles_to_failure(
                sig_p, a, b, BOND_ENDURANCE_LIMIT_MPa
            )
            life_y = (nf / CYCLES_PER_YEAR) if math.isfinite(nf) else float("inf")
            nf_str = "inf" if math.isinf(nf) else (
                f"{nf:.2g}" if nf >= 1 else f"{nf:.3f}"
            )
            life_str = fmt_life(life_y) if math.isinf(life_y) else (
                f"{life_y:.2f} y" if life_y >= 1.0 else fmt_life(life_y)
            )
            print(f"{d_alpha_ppm:>10.0f}  {rec:>10.2f}  "
                  f"{sig_p:>10.2f} MPa  "
                  f"{sf:>11.2f}   "
                  f"{nf_str:>12}  {life_str:>14}")
            sens_rows.append({
                "delta_alpha_ppm_per_K": d_alpha_ppm,
                "peel_recovery_factor": rec,
                "peak_peel_MPa": round(sig_p, 3),
                "static_SF": round(sf, 3),
                "cycles_to_failure": (
                    None if math.isinf(nf) else round(nf, 4)
                ),
                "fatigue_life_years": (
                    None if math.isinf(life_y) else round(life_y, 3)
                ),
            })
    print()

    # --- Plot: fatigue life vs delta-alpha for several recovery factors ---
    fig, ax = plt.subplots(figsize=(9, 5.5))
    d_alpha_grid = np.linspace(5, 35, 121) * 1e-6
    for rec in (0.30, 0.40, 0.50, 0.70, 1.00):
        lives = []
        for d_a in d_alpha_grid:
            sig_int = constrained_thermal_stress_MPa(
                E_TREAD_PA, d_a, DELTA_T_FULL_K
            )
            sig_p = sig_int * rec
            nf = cycles_to_failure(sig_p, a, b, BOND_ENDURANCE_LIMIT_MPa)
            life_y = nf / CYCLES_PER_YEAR if math.isfinite(nf) else 1e9
            lives.append(life_y)
        ax.plot(d_alpha_grid * 1e6, lives, label=f"recovery = {rec:.2f}", marker="")
    ax.axvline(DELTA_ALPHA * 1e6, color="black", linestyle=":",
               alpha=0.6, label=f"nominal Δα = {DELTA_ALPHA*1e6:.1f} ppm/K")
    ax.axhline(1.0, color="red", linestyle="--", alpha=0.5,
               label="1 year design life")
    ax.set_yscale("log")
    ax.set_xlabel("Differential CTE  Δα = α_tread − α_skin  (ppm/K)")
    ax.set_ylabel("Bond fatigue life (years)")
    ax.set_title("AURORA-Mono — thermal-cycle bond fatigue life\n"
                 "(ΔT = 300 K full lunar diurnal swing)")
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.set_ylim(1e-3, 1e6)
    fig.tight_layout()
    fig.savefig("plots/thermal_cycle_fatigue_life.png", dpi=120)
    print("Wrote plots/thermal_cycle_fatigue_life.png")

    # --- CSV outputs ---
    summary = {
        "E_tread_GPa": E_TREAD_PA / 1e9,
        "E_skin_GPa": E_SKIN_PA / 1e9,
        "alpha_tread_ppm_per_K": ALPHA_TREAD * 1e6,
        "alpha_skin_ppm_per_K": ALPHA_SKIN * 1e6,
        "delta_alpha_ppm_per_K": DELTA_ALPHA * 1e6,
        "delta_T_full_K": DELTA_T_FULL_K,
        "cycles_per_year": round(CYCLES_PER_YEAR, 2),
        "bond_effective_allowable_MPa": BOND_EFFECTIVE_PEEL_MPa,
        "bond_endurance_limit_MPa": BOND_ENDURANCE_LIMIT_MPa,
        "peel_recovery_nominal": PEEL_RECOVERY_NOMINAL,
        "interior_constrained_full_MPa": round(sigma_interior_full, 3),
        "interior_constrained_half_MPa": round(sigma_interior_half, 3),
        "edge_peel_full_MPa": round(sigma_peel_full, 3),
        "edge_peel_half_MPa": round(sigma_peel_half, 3),
        "static_SF_edge_peel_full": round(sf_peel_full, 3),
        "static_SF_edge_peel_half": round(sf_peel_half, 3),
        "cycles_to_failure_nominal": (
            None if math.isinf(N_f) else round(N_f, 4)
        ),
        "fatigue_life_years_nominal": (
            None if math.isinf(life_years) else round(life_years, 3)
        ),
    }
    pd.DataFrame([summary]).to_csv("thermal_cycle_check_summary.csv", index=False)
    pd.DataFrame(sens_rows).to_csv(
        "thermal_cycle_check_sensitivity.csv", index=False
    )
    print("Wrote thermal_cycle_check_summary.csv")
    print("Wrote thermal_cycle_check_sensitivity.csv")
    print()

    # --- Verdict ---
    print("=" * 64)
    print("VERDICT (honest)")
    print("=" * 64)
    if sf_peel_full >= 2.0:
        head = "Adequate margin."
    elif sf_peel_full >= 1.0:
        head = "Marginal."
    else:
        head = "MARGIN CONCERN."
    print(f"{head} Nominal edge-peel SF = {sf_peel_full:.2f} against the "
          f"bond's {BOND_EFFECTIVE_PEEL_MPa:.0f} MPa effective allowable.")
    print()
    print("The constrained-thermal upper bound is conservative because it "
          "ignores:")
    print("  - viscoelastic relaxation during long lunar-day dwells "
          "(real, significant for PEKK near +127 C)")
    print("  - through-thickness compliance of the sandwich wall")
    print("  - any compliant interlayer between SiC-PEKK and PEKK-CNT/CF")
    print()
    print("Even so, the result strongly suggests thermal cycling is the "
          "dominant failure mode candidate for this design, in contrast")
    print("to the driving-load checks where margins were comfortable.")
    print()
    print("Mitigations to consider in any next design iteration:")
    print("  - Compliant interlayer (e.g. neat PEKK strip) between tread "
          "and skin to absorb CTE mismatch")
    print("  - Reduce delta_alpha by reformulating SiC-PEKK with higher "
          "SiC vol-fraction (drops alpha_tread)")
    print("  - Reduce delta_alpha by lowering skin reinforcement (raises "
          "alpha_skin) -- trades against skin strength")
    print("  - Edge geometry (chamfered lug bases, scalloped transitions) "
          "to spread the strain singularity")
    print("  - Active or passive thermal management to limit "
          "delta_T at the bond")
    print()
    print("Next-fidelity step: viscoelastic FEM (Prony series for PEKK), "
          "with the actual measured CTE values for both formulations.")


if __name__ == "__main__":
    main()
