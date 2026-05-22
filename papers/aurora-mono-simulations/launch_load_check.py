
"""
Launch-load screening check.

Spaceflight hardware typically sees three classes of launch load:

  (1) Quasi-static (QS) acceleration       -- sustained, multi-g
      Typical launch vehicle: 4-8 g axial, 2-4 g lateral.
  (2) Random vibration                      -- broadband 20-2000 Hz
      Reacted as an equivalent static load via Miles' equation:
          G_response_RMS = sqrt( (pi/2) * f_n * Q * PSD(f_n) )
          G_eq_3sigma    = 3 * G_response_RMS
  (3) Pyro shock                            -- short, high-frequency
      Not analyzed here (typically governs small electronics, not
      composite structures).

The wheel, treated as a 2.30 kg mass at the wheel CG and restrained
at the hub bolts, sees these loads as inertial reactions transmitted
through the hub joint. This script computes the per-bolt loads under
launch and reuses the bolt-joint mechanics from `bolt_joint_check.py`
to evaluate SFs.

What this DOES cover:
  - QS loads in each axis at typical launch-vehicle g-levels
  - Random-vib equivalent static via Miles' equation, swept over
    natural frequencies 50-2000 Hz
  - First-mode natural-frequency estimate (wheel as a lumped mass on
    the 6 composite hub web spokes)
  - Hub bolt joint SFs under launch loads (yield, separation, pad
    compression)
  - Sensitivity on input PSD level and damping (Q)

What this does NOT cover:
  - Coupled-loads analysis with the rover and launch vehicle
  - Modal analysis with realistic boundary conditions (rover
    suspension restraint, not free-free wheel)
  - Sine-burst tests, pyro shock
  - Acoustic loading on the wheel surface
  - Stress in the rim/lattice/skin under inertial body loads
    (only the hub joint is checked; lattice / skin response to
    distributed inertial loading should be added separately)
  - Time-domain transient response
"""

import math
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from bolt_joint_check import (
    BOLT_MATERIALS, NOMINAL_BOLT_MATL,
    JOINT_STIFFNESS_RATIO_C, PRELOAD_FACTOR_NOMINAL,
    bolt_check, per_bolt_loads,
    pad_boss_compressive_stress_MPa,
    BOLT_MAJOR_DIA_M, PAD_BOSS_DIA_M,
    COMPOSITE_COMPRESSION_ALLOWABLE_MPa,
)


# ============================================================
# Wheel mass and orientation
# ============================================================
WHEEL_MASS_KG = 2.30           # nominal as-built mass from build spec
G_EARTH = 9.81

# Quasi-static launch envelope (typical launch vehicle)
QS_AXIAL_G = 6.0               # along the launch direction
QS_LATERAL_G = 3.0             # perpendicular to launch

# Random vibration: typical payload qualification PSD level (flat)
PSD_NOMINAL_g2_per_Hz = 0.04   # general-payload qualification level
PSD_HIGH_g2_per_Hz = 0.10      # aggressive qualification level
PSD_LOW_g2_per_Hz = 0.01       # low-vibration mission

DAMPING_RATIO_NOMINAL = 0.05   # 5% (typical aerospace assumption)
Q_NOMINAL = 1.0 / (2.0 * DAMPING_RATIO_NOMINAL)   # = 10


# ============================================================
# Hub spoke geometry (from build spec)
# ============================================================
N_HUB_SPOKES = 6
SPOKE_THICKNESS_HUB_M = 0.0050    # 5 mm at hub boss
SPOKE_THICKNESS_RIM_M = 0.0030    # 3 mm at inner rim
SPOKE_THICKNESS_AVG_M = 0.5 * (SPOKE_THICKNESS_HUB_M + SPOKE_THICKNESS_RIM_M)
SPOKE_WIDTH_M = 0.030             # estimate: 30 mm axial width
HUB_PILOT_RADIUS_M = (3.185 * 0.0254) / 2.0
RIM_INNER_RADIUS_M = (16.8 * 0.0254 / 2.0) - 0.0094  # rim OD minus full wall
SPOKE_LENGTH_M = RIM_INNER_RADIUS_M - HUB_PILOT_RADIUS_M

E_PEKK_CNT_CF_PA = 30.0e9


# ============================================================
# Miles' equation
# ============================================================
def miles_equation_g_rms(f_n_Hz, Q, PSD_g2_per_Hz):
    """3-sigma equivalent static G level for a SDOF mass response to
    base random excitation at the natural frequency."""
    return math.sqrt((math.pi / 2.0) * f_n_Hz * Q * PSD_g2_per_Hz)


def miles_g_3sigma(f_n_Hz, Q, PSD_g2_per_Hz):
    return 3.0 * miles_equation_g_rms(f_n_Hz, Q, PSD_g2_per_Hz)


# ============================================================
# First-mode estimate: lumped mass on parallel spokes
# ============================================================
def first_mode_estimate_Hz():
    """Treat the wheel as a lumped mass on N_HUB_SPOKES parallel beam
    springs (each spoke is a cantilever from the hub to the rim,
    bending in its weak direction)."""
    # Single-spoke stiffness in radial bending (worst direction):
    # k = 3 * E * I / L^3 for a cantilever
    I_min = SPOKE_WIDTH_M * SPOKE_THICKNESS_AVG_M ** 3 / 12.0
    k_single_N_per_m = 3.0 * E_PEKK_CNT_CF_PA * I_min / SPOKE_LENGTH_M ** 3
    # Parallel spokes share the load
    k_total = N_HUB_SPOKES * k_single_N_per_m
    f_n_Hz = (1.0 / (2.0 * math.pi)) * math.sqrt(k_total / WHEEL_MASS_KG)
    return f_n_Hz, k_total, k_single_N_per_m


# ============================================================
# Decompose launch load into hub bolt loads
# ============================================================
WHEEL_OD_M = 18.0 * 0.0254
WHEEL_WIDTH_M = 8.0 * 0.0254

def launch_load_per_bolt(F_axial_wheel_N, F_radial_wheel_N):
    """Compute per-bolt tension and shear from a launch inertial load
    on the wheel. F_axial_wheel = force along wheel rotation axis;
    F_radial_wheel = force perpendicular to wheel axis."""
    # Axial force along the wheel axis tries to pull the wheel off
    # the hub -> direct bolt tension shared equally
    F_tension_per_bolt = F_axial_wheel_N / 8

    # Radial force creates the same eccentric-moment situation as the
    # driving check (radial load at wheel mid-plane, offset from bolt
    # plane by half-width)
    pb = per_bolt_loads(F_radial_wheel_N, 0.0, 0.0)
    F_tension_per_bolt_radial = pb["tension_per_bolt_N"]
    F_shear_per_bolt = pb["shear_per_bolt_N"]

    # Worst-case combine: assume both axes load simultaneously
    F_tension_total = F_tension_per_bolt + F_tension_per_bolt_radial
    return {
        "tension_per_bolt_N": F_tension_total,
        "shear_per_bolt_N":   F_shear_per_bolt,
        "from_axial_N":       F_tension_per_bolt,
        "from_radial_N":      F_tension_per_bolt_radial,
    }


# ============================================================
# Main
# ============================================================
def main():
    os.makedirs("plots", exist_ok=True)

    print("=" * 64)
    print("Launch-load screening check")
    print("=" * 64)
    print(f"Wheel mass:               {WHEEL_MASS_KG:.2f} kg")
    print(f"Earth g:                  {G_EARTH:.2f} m/s²")
    print()
    print(f"Quasi-static envelope:")
    print(f"  Axial:                  {QS_AXIAL_G:.1f} g")
    print(f"  Lateral:                {QS_LATERAL_G:.1f} g")
    print()
    print(f"Random vibration envelope (flat PSD assumption):")
    print(f"  Nominal payload:        {PSD_NOMINAL_g2_per_Hz:.3f} g²/Hz")
    print(f"  Aggressive qual:        {PSD_HIGH_g2_per_Hz:.3f} g²/Hz")
    print(f"  Low-vibration mission:  {PSD_LOW_g2_per_Hz:.3f} g²/Hz")
    print(f"  Damping ratio:          {DAMPING_RATIO_NOMINAL:.2f} (Q = {Q_NOMINAL:.0f})")
    print()

    # --- First mode estimate ---
    f_n_estimate, k_total, k_single = first_mode_estimate_Hz()
    print("First-mode estimate (lumped wheel mass on 6 parallel spokes):")
    print(f"  Spoke length:             {SPOKE_LENGTH_M*1000:.1f} mm")
    print(f"  Spoke avg thickness:      {SPOKE_THICKNESS_AVG_M*1000:.1f} mm")
    print(f"  Single-spoke stiffness:   {k_single/1e3:.1f} N/mm")
    print(f"  Total stiffness (6 //):   {k_total/1e3:.1f} N/mm")
    print(f"  First mode estimate:      {f_n_estimate:.0f} Hz")
    print()
    if f_n_estimate >= 100:
        f_n_note = (
            "Above the typical 50-100 Hz threshold; wheel is unlikely "
            "to resonate at the heart of the launch random-vib spectrum."
        )
    else:
        f_n_note = (
            "Below the 100 Hz threshold; wheel may resonate within "
            "the launch random-vib band -- additional analysis needed."
        )
    print(f"  Note: {f_n_note}")
    print()

    # --- Quasi-static case ---
    F_axial_QS = WHEEL_MASS_KG * G_EARTH * QS_AXIAL_G
    F_lateral_QS = WHEEL_MASS_KG * G_EARTH * QS_LATERAL_G
    print(f"Quasi-static loads at the wheel CG:")
    print(f"  F_axial   = m·g·{QS_AXIAL_G:.0f} = {F_axial_QS:.1f} N")
    print(f"  F_lateral = m·g·{QS_LATERAL_G:.0f} = {F_lateral_QS:.1f} N")
    print()

    # --- Random vibration: Miles' equivalent at the f_n estimate ---
    G_rv_nominal = miles_g_3sigma(
        f_n_estimate, Q_NOMINAL, PSD_NOMINAL_g2_per_Hz
    )
    F_rv = WHEEL_MASS_KG * G_EARTH * G_rv_nominal
    print(f"Random-vib equivalent (Miles, nominal PSD, f_n = "
          f"{f_n_estimate:.0f} Hz):")
    print(f"  3-sigma equiv G:        {G_rv_nominal:.1f} g")
    print(f"  Equivalent force:       {F_rv:.1f} N")
    print()

    # --- Combined launch load (worst case: QS + RV vectorial) ---
    F_axial_combined = math.sqrt(F_axial_QS ** 2 + F_rv ** 2)
    F_lateral_combined = math.sqrt(F_lateral_QS ** 2 + F_rv ** 2)
    print(f"Combined launch loads (worst-case axial + lateral, "
          f"QS + RV vectorial):")
    print(f"  F_axial_combined:       {F_axial_combined:.1f} N")
    print(f"  F_lateral_combined:     {F_lateral_combined:.1f} N")
    print()

    # --- Apply to bolt joint ---
    matl = BOLT_MATERIALS[NOMINAL_BOLT_MATL]

    # QS-only case
    pb_QS = launch_load_per_bolt(F_axial_QS, F_lateral_QS)
    chk_QS = bolt_check(pb_QS["tension_per_bolt_N"],
                        pb_QS["shear_per_bolt_N"], matl)
    pad_QS_MPa = pad_boss_compressive_stress_MPa(
        chk_QS["preload_N"], PAD_BOSS_DIA_M, BOLT_MAJOR_DIA_M
    )

    # Combined QS + RV
    pb_combined = launch_load_per_bolt(F_axial_combined, F_lateral_combined)
    chk_combined = bolt_check(pb_combined["tension_per_bolt_N"],
                              pb_combined["shear_per_bolt_N"], matl)
    pad_comb_MPa = pad_boss_compressive_stress_MPa(
        chk_combined["preload_N"], PAD_BOSS_DIA_M, BOLT_MAJOR_DIA_M
    )

    print(f"Hub bolt joint SFs under launch loads "
          f"({NOMINAL_BOLT_MATL}, "
          f"{PRELOAD_FACTOR_NOMINAL:.0%} preload, C = "
          f"{JOINT_STIFFNESS_RATIO_C:.2f}):")
    print(f"{'Case':<28}  {'F_tension':>10}  {'F_shear':>9}  "
          f"{'yield SF':>9}  {'sep SF':>8}  {'pad SF':>8}")
    for label, pb, chk, pad_MPa in (
        ("Quasi-static only",   pb_QS,        chk_QS,       pad_QS_MPa),
        ("QS + Miles RV nom",   pb_combined,  chk_combined, pad_comb_MPa),
    ):
        sep_str = (
            "∞" if math.isinf(chk["separation_SF"])
            else f"{chk['separation_SF']:.1f}"
        )
        pad_SF = COMPOSITE_COMPRESSION_ALLOWABLE_MPa / pad_MPa
        print(f"{label:<28}  {pb['tension_per_bolt_N']:>8.1f} N  "
              f"{pb['shear_per_bolt_N']:>7.1f} N  "
              f"{chk['yield_SF']:>9.2f}  {sep_str:>8}  {pad_SF:>8.2f}")
    print()

    # === Compare launch to operational ===
    print("Launch vs operational comparison (per-bolt loads):")
    OPS_MAX_RADIAL_N = 612.4  # from main screening model
    pb_ops = launch_load_per_bolt(0.0, OPS_MAX_RADIAL_N)
    print(f"  Worst rock event (driving):  "
          f"tension/bolt = {pb_ops['tension_per_bolt_N']:6.1f} N  "
          f"shear/bolt = {pb_ops['shear_per_bolt_N']:6.1f} N")
    print(f"  QS-only launch:              "
          f"tension/bolt = {pb_QS['tension_per_bolt_N']:6.1f} N  "
          f"shear/bolt = {pb_QS['shear_per_bolt_N']:6.1f} N")
    print(f"  QS + RV combined:            "
          f"tension/bolt = {pb_combined['tension_per_bolt_N']:6.1f} N  "
          f"shear/bolt = {pb_combined['shear_per_bolt_N']:6.1f} N")
    if pb_combined["tension_per_bolt_N"] > pb_ops["tension_per_bolt_N"]:
        print("  -> Launch tension exceeds operational; launch is the "
              "governing tension case.")
    else:
        print("  -> Operational tension exceeds launch; driving loads "
              "remain the governing tension case.")
    print()

    # ============================================================
    # Sensitivity sweep: PSD level x natural frequency
    # ============================================================
    print("Sensitivity sweep (random-vib): G_eq vs f_n at three PSD levels")
    print(f"{'f_n (Hz)':>10}  {'PSD low (g)':>13}  "
          f"{'PSD nom (g)':>13}  {'PSD high (g)':>14}  "
          f"{'yield SF (nom)':>15}  {'pad SF (nom)':>13}")
    sens_rows = []
    f_n_grid = [50, 100, 200, 500, 1000, 2000]
    for f_n in f_n_grid:
        G_low = miles_g_3sigma(f_n, Q_NOMINAL, PSD_LOW_g2_per_Hz)
        G_nom = miles_g_3sigma(f_n, Q_NOMINAL, PSD_NOMINAL_g2_per_Hz)
        G_high = miles_g_3sigma(f_n, Q_NOMINAL, PSD_HIGH_g2_per_Hz)
        # Apply nominal-PSD case to the bolt joint
        F_rv_nom = WHEEL_MASS_KG * G_EARTH * G_nom
        F_axial_c = math.sqrt(F_axial_QS ** 2 + F_rv_nom ** 2)
        F_lateral_c = math.sqrt(F_lateral_QS ** 2 + F_rv_nom ** 2)
        pb_c = launch_load_per_bolt(F_axial_c, F_lateral_c)
        chk_c = bolt_check(pb_c["tension_per_bolt_N"],
                           pb_c["shear_per_bolt_N"], matl)
        pad_c_MPa = pad_boss_compressive_stress_MPa(
            chk_c["preload_N"], PAD_BOSS_DIA_M, BOLT_MAJOR_DIA_M
        )
        pad_c_SF = COMPOSITE_COMPRESSION_ALLOWABLE_MPa / pad_c_MPa
        print(f"{f_n:>10.0f}  {G_low:>11.1f} g  "
              f"{G_nom:>11.1f} g  {G_high:>12.1f} g  "
              f"{chk_c['yield_SF']:>15.2f}  {pad_c_SF:>13.2f}")
        sens_rows.append({
            "f_n_Hz":              f_n,
            "G_3sigma_PSD_low":    round(G_low, 2),
            "G_3sigma_PSD_nominal": round(G_nom, 2),
            "G_3sigma_PSD_high":   round(G_high, 2),
            "yield_SF_nominal_PSD": round(chk_c["yield_SF"], 3),
            "pad_SF_nominal_PSD":  round(pad_c_SF, 3),
        })
    print()

    # ============================================================
    # Plot: G_eq vs f_n for three PSD levels
    # ============================================================
    fig, ax = plt.subplots(figsize=(9, 5.5))
    f_n_smooth = np.logspace(math.log10(20), math.log10(2000), 200)
    for psd, label, color in (
        (PSD_LOW_g2_per_Hz, "Low-vib mission (0.01 g²/Hz)", "tab:green"),
        (PSD_NOMINAL_g2_per_Hz, "Nominal payload (0.04 g²/Hz)", "tab:blue"),
        (PSD_HIGH_g2_per_Hz, "Aggressive qual (0.10 g²/Hz)", "tab:red"),
    ):
        Gs = [miles_g_3sigma(f, Q_NOMINAL, psd) for f in f_n_smooth]
        ax.plot(f_n_smooth, Gs, label=label, color=color, linewidth=2)
    ax.axvline(f_n_estimate, color="black", linestyle=":", alpha=0.6,
               label=f"Estimated f_n ≈ {f_n_estimate:.0f} Hz")
    ax.axhline(QS_AXIAL_G, color="gray", linestyle="--", alpha=0.5,
               label=f"QS axial = {QS_AXIAL_G:.0f} g (for comparison)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("First natural frequency f_n (Hz)")
    ax.set_ylabel("3σ equivalent static G level (Miles' eq, Q = 10)")
    ax.set_title("AURORA-Mono — launch random-vib equivalent G "
                 "vs natural frequency")
    ax.grid(True, which="both", linestyle="--", alpha=0.4)
    ax.legend(fontsize=9, loc="lower right")
    fig.tight_layout()
    fig.savefig("plots/launch_load_miles.png", dpi=120)
    print("Wrote plots/launch_load_miles.png")

    # ============================================================
    # CSV outputs
    # ============================================================
    summary = {
        "wheel_mass_kg":                WHEEL_MASS_KG,
        "qs_axial_g":                   QS_AXIAL_G,
        "qs_lateral_g":                 QS_LATERAL_G,
        "psd_nominal_g2_per_Hz":        PSD_NOMINAL_g2_per_Hz,
        "Q":                            Q_NOMINAL,
        "f_n_estimate_Hz":              round(f_n_estimate, 1),
        "G_3sigma_at_f_n_Hz":           round(G_rv_nominal, 2),
        "F_axial_QS_N":                 round(F_axial_QS, 2),
        "F_lateral_QS_N":               round(F_lateral_QS, 2),
        "F_rv_nominal_N":               round(F_rv, 2),
        "F_axial_combined_N":           round(F_axial_combined, 2),
        "F_lateral_combined_N":         round(F_lateral_combined, 2),
        "tension_per_bolt_QS_N":        round(pb_QS["tension_per_bolt_N"], 2),
        "shear_per_bolt_QS_N":          round(pb_QS["shear_per_bolt_N"], 2),
        "tension_per_bolt_combined_N":  round(
            pb_combined["tension_per_bolt_N"], 2
        ),
        "shear_per_bolt_combined_N":    round(
            pb_combined["shear_per_bolt_N"], 2
        ),
        "yield_SF_QS":                  round(chk_QS["yield_SF"], 3),
        "yield_SF_combined":            round(chk_combined["yield_SF"], 3),
        "pad_SF_QS":                    round(
            COMPOSITE_COMPRESSION_ALLOWABLE_MPa / pad_QS_MPa, 3
        ),
        "pad_SF_combined":              round(
            COMPOSITE_COMPRESSION_ALLOWABLE_MPa / pad_comb_MPa, 3
        ),
    }
    pd.DataFrame([summary]).to_csv(
        "launch_load_check_summary.csv", index=False
    )
    pd.DataFrame(sens_rows).to_csv(
        "launch_load_check_sensitivity.csv", index=False
    )
    print("Wrote launch_load_check_summary.csv")
    print("Wrote launch_load_check_sensitivity.csv")
    print()

    # ============================================================
    # Verdict
    # ============================================================
    print("=" * 64)
    print("VERDICT")
    print("=" * 64)
    yield_SF_combined = chk_combined["yield_SF"]
    pad_SF_combined = COMPOSITE_COMPRESSION_ALLOWABLE_MPa / pad_comb_MPa
    governing = min(yield_SF_combined, pad_SF_combined)
    governing_label = (
        "bolt yield" if yield_SF_combined <= pad_SF_combined
        else "pad-boss compression"
    )
    print(f"Governing margin under combined QS + RV launch loads: "
          f"{governing_label} (SF = {governing:.2f})")
    print()
    if pb_combined["tension_per_bolt_N"] > pb_ops["tension_per_bolt_N"]:
        load_note = (
            "Launch tension per bolt exceeds operational tension. "
            "Launch is the GOVERNING load case for the hub joint."
        )
    else:
        load_note = (
            "Operational driving loads remain larger than launch loads "
            "for this geometry."
        )
    print(load_note)
    print()
    if governing >= 1.5:
        v = ("Comfortable margin on launch loads. The joint can survive "
             "the modeled launch envelope without modification.")
    elif governing >= 1.0:
        v = ("Marginal launch margin. Consider higher-grade bolts, "
             "lower preload, or design changes to raise the natural "
             "frequency and reduce Miles' response.")
    else:
        v = ("INSUFFICIENT launch margin. The joint as specified would "
             "not survive a nominal launch random-vib environment.")
    print(v)
    print()
    print("Notes on what this screening does NOT capture:")
    print("  - Lattice and skin response to distributed inertial loads "
          "(only the hub joint is checked)")
    print("  - Modal analysis with realistic suspension boundary "
          "conditions")
    print("  - Pyro shock, acoustic loading")
    print("  - Coupled-loads analysis with launch vehicle response")


if __name__ == "__main__":
    main()
