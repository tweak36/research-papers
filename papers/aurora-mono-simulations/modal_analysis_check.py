
"""
Modal analysis screening check.

Wheel natural frequencies, evaluated as closed-form mode estimates for
each plausible mode family and compared against the launch random-vib
envelope. This refines the single-DOF estimate from launch_load_check.py
by enumerating multiple modes and identifying which fall inside the
worst part of the launch spectrum.

Modes evaluated:

  (1) Spoke bending mode (wheel-on-spokes, translational)
      Treats the wheel as a lumped mass on the 6 hub spokes acting in
      parallel as cantilever beams. Frequency depends strongly on
      suspension boundary stiffness; swept over a plausible range.

  (2,3,4) Rim ring modes n = 2, 3, 4
      In-plane bending modes of the rim treated as a thin circular ring.
      Love / Soedel closed-form for thin-ring vibration:
          omega_n = (n(n^2 - 1) / sqrt(n^2 + 1)) * sqrt(EI / (m' R^4))
      where n is the circumferential mode number, EI is the rim wall's
      bending stiffness (dominated by the sandwich skins via parallel-
      axis theorem), m' is the rim mass per unit length, R is the mean
      rim radius. n=2 is the "ovalization" mode; n=3 is "triangular";
      n=4 is "square."

  (T) Rim torsional mode
      First torsional mode of the rim about the wheel axis. Restoring
      stiffness from the spokes' tangential bending; inertia is the
      rim's polar moment about the wheel axis.

What this check does:
  - Estimates the first 5 natural frequencies of the wheel
  - Computes Miles' equation 3-sigma equivalent G at each mode for the
    nominal launch PSD
  - Identifies which modes fall in the 20-2000 Hz launch random-vib band
  - Sensitivity sweep on suspension stiffness for the spoke-bending mode

What this does NOT cover:
  - Coupled modes (interaction between rim, spokes, hub, suspension)
  - Mode shapes (only natural frequencies)
  - Full 3D eigenanalysis with realistic boundary conditions
  - Out-of-plane (axial) rim modes
  - Coupling with the rover suspension / chassis (would require
    coupled-loads analysis)
  - Damping beyond a single Q-value assumption
"""

import math
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# Geometry from the AURORA-Mono build spec
# ============================================================
IN = 0.0254

WHEEL_MASS_KG = 2.30
WHEEL_OD_M = 18.0 * IN
RIM_OD_M = 16.8 * IN              # rim outer diameter, pre-tread
WHEEL_WIDTH_M = 8.0 * IN
CORE_HEIGHT_M = 0.0070
SKIN_THICKNESS_M = 0.0012
HUB_PILOT_RADIUS_M = (3.185 * IN) / 2.0

RIM_MEAN_R_M = (RIM_OD_M / 2.0) - SKIN_THICKNESS_M - CORE_HEIGHT_M / 2.0
LATTICE_CIRC_M = 2.0 * math.pi * RIM_MEAN_R_M

# Spoke geometry (matches launch_load_check.py)
N_HUB_SPOKES = 6
SPOKE_THICKNESS_AVG_M = 0.5 * (0.0050 + 0.0030)  # 4.0 mm
SPOKE_WIDTH_M = 0.030                              # 30 mm axial
SPOKE_LENGTH_M = (RIM_OD_M / 2.0 - 0.0094) - HUB_PILOT_RADIUS_M

# Materials
E_PEKK_CNT_CF_PA = 30.0e9
NU_PEKK_CNT_CF = 0.35
G_PEKK_CNT_CF_PA = E_PEKK_CNT_CF_PA / (2.0 * (1.0 + NU_PEKK_CNT_CF))
E_SKIN_PA = 50.0e9   # skin in-plane modulus
RHO_PEKK_CNT_CF = 1450.0   # kg/m^3, approximate

# Tread is heavier; for rim mass estimation, treat rim as composite mass
# distributed around the circumference
# Estimate rim mass = total wheel mass minus hub/spoke portion (~30%)
RIM_MASS_KG = WHEEL_MASS_KG * 0.75
RIM_MASS_PER_LENGTH_KG_PER_M = RIM_MASS_KG / LATTICE_CIRC_M


# ============================================================
# Sandwich-rim bending stiffness EI (about radial bending axis)
# ============================================================
# Parallel-axis dominated by the two skins offset from the rim
# centerline by (core + skin) / 2
d_skin_centerline_M = (CORE_HEIGHT_M + SKIN_THICKNESS_M) / 2.0
I_one_skin_M4 = (
    WHEEL_WIDTH_M * SKIN_THICKNESS_M * d_skin_centerline_M ** 2
)
EI_RIM_NM2 = E_SKIN_PA * 2.0 * I_one_skin_M4


# ============================================================
# Spoke bending stiffness (matches launch_load_check.py)
# ============================================================
def spoke_stiffness_per_spoke_N_per_m(boundary_factor=3.0):
    """Single-spoke stiffness in radial bending.

    boundary_factor = 3.0 -> cantilever (free at rim end, fixed at hub)
    boundary_factor = 12.0 -> fixed-fixed (both ends clamped: rim
                              constrained by symmetric loading +
                              stiff suspension)
    Intermediate values bracket realistic boundary conditions.
    """
    I_min = SPOKE_WIDTH_M * SPOKE_THICKNESS_AVG_M ** 3 / 12.0
    return boundary_factor * E_PEKK_CNT_CF_PA * I_min / SPOKE_LENGTH_M ** 3


def spoke_mode_Hz(boundary_factor=3.0):
    k_one = spoke_stiffness_per_spoke_N_per_m(boundary_factor)
    k_total = N_HUB_SPOKES * k_one
    return (1.0 / (2.0 * math.pi)) * math.sqrt(k_total / WHEEL_MASS_KG)


# ============================================================
# Ring modes (Love / Soedel)
# ============================================================
def ring_mode_Hz(n):
    """In-plane ring bending mode of circumferential order n (n >= 2)."""
    if n < 2:
        return None
    factor = n * (n ** 2 - 1) / math.sqrt(n ** 2 + 1)
    omega = factor * math.sqrt(
        EI_RIM_NM2 / (RIM_MASS_PER_LENGTH_KG_PER_M * RIM_MEAN_R_M ** 4)
    )
    return omega / (2.0 * math.pi)


# ============================================================
# Rim torsional mode (first)
# ============================================================
def torsional_mode_Hz():
    """First torsional mode of the rim about the wheel axis.

    Restoring stiffness: spokes in tangential bending. Inertia: rim's
    polar moment of inertia about the wheel axis. Simplified to a
    single-DOF rotational analog.
    """
    # Tangential bending stiffness per spoke (same formula as radial,
    # but the spoke bends in its "wide" direction -> larger I)
    I_max_tangential = (
        SPOKE_THICKNESS_AVG_M * SPOKE_WIDTH_M ** 3 / 12.0
    )
    k_tang_one = (
        3.0 * E_PEKK_CNT_CF_PA * I_max_tangential / SPOKE_LENGTH_M ** 3
    )
    # Convert linear stiffness at the rim radius into rotational
    # stiffness about the wheel axis
    k_theta_per_spoke = k_tang_one * (RIM_MEAN_R_M ** 2)
    k_theta_total = N_HUB_SPOKES * k_theta_per_spoke
    # Rim polar inertia (thin ring approximation)
    J_rim = RIM_MASS_KG * RIM_MEAN_R_M ** 2
    return (1.0 / (2.0 * math.pi)) * math.sqrt(k_theta_total / J_rim)


# ============================================================
# Miles' equation (matches launch_load_check.py)
# ============================================================
PSD_LAUNCH_NOMINAL_g2_per_Hz = 0.04
PSD_LOW = 0.01
PSD_HIGH = 0.10
DAMPING_RATIO = 0.05
Q = 1.0 / (2.0 * DAMPING_RATIO)


def miles_3sigma_g(f_n_Hz, PSD=PSD_LAUNCH_NOMINAL_g2_per_Hz):
    if f_n_Hz <= 0:
        return 0.0
    g_rms = math.sqrt((math.pi / 2.0) * f_n_Hz * Q * PSD)
    return 3.0 * g_rms


# ============================================================
# Main
# ============================================================
def main():
    os.makedirs("plots", exist_ok=True)

    print("=" * 64)
    print("Modal analysis screening (closed-form, NOT 3D eigenanalysis)")
    print("=" * 64)
    print(f"Wheel mass:                {WHEEL_MASS_KG:.2f} kg")
    print(f"Rim mean radius:           {RIM_MEAN_R_M*1000:.1f} mm")
    print(f"Rim mass per unit length:  "
          f"{RIM_MASS_PER_LENGTH_KG_PER_M:.2f} kg/m")
    print(f"Rim sandwich EI (bending): {EI_RIM_NM2:.1f} N·m²")
    print()

    # Spoke mode at nominal boundary (cantilever)
    f_spoke_free = spoke_mode_Hz(boundary_factor=3.0)
    f_spoke_clamped = spoke_mode_Hz(boundary_factor=12.0)

    # Rim ring modes
    f_ring2 = ring_mode_Hz(2)
    f_ring3 = ring_mode_Hz(3)
    f_ring4 = ring_mode_Hz(4)

    # Torsional mode
    f_tors = torsional_mode_Hz()

    modes = [
        ("Spoke bending, free (cantilever) — launch-check baseline",
         f_spoke_free),
        ("Spoke bending, clamped (stiff suspension upper bound)",
         f_spoke_clamped),
        ("Rim ring mode n=2 (ovalization)", f_ring2),
        ("Rim ring mode n=3 (triangular)", f_ring3),
        ("Rim ring mode n=4 (square)", f_ring4),
        ("Rim torsional, first mode", f_tors),
    ]

    print(f"Estimated wheel natural frequencies and Miles' 3σ "
          f"response at each:")
    print(f"  (Launch PSD = {PSD_LAUNCH_NOMINAL_g2_per_Hz:.3f} g²/Hz, "
          f"Q = {Q:.0f})")
    print()
    print(f"{'Mode':<58}  {'f_n (Hz)':>10}  {'G_3σ (g)':>10}  "
          f"{'in 50-800 Hz band?':>20}")
    print("-" * 105)
    rows = []
    for label, f in modes:
        if f is None:
            continue
        g_3s = miles_3sigma_g(f)
        in_band = "YES" if 50 <= f <= 800 else "no"
        print(f"{label:<58}  {f:>9.1f}  {g_3s:>9.1f}  {in_band:>20}")
        rows.append({
            "mode": label,
            "f_n_Hz": round(f, 2),
            "G_3sigma_g_nominal_PSD": round(g_3s, 2),
            "in_50_800_Hz_band": (50 <= f <= 800),
            "F_inertial_N_at_wheel_mass":
                round(WHEEL_MASS_KG * 9.81 * g_3s, 1),
        })
    print()

    # Suspension stiffness sensitivity for the spoke-bending mode
    print("Suspension boundary sensitivity (spoke-bending mode only):")
    print(f"{'Boundary factor':>18}  {'Interpretation':<40}  "
          f"{'f_spoke (Hz)':>14}")
    boundary_cases = [
        (3.0, "Free at rim end (cantilever) -- soft mount"),
        (6.0, "Intermediate (typical bolted joint)"),
        (12.0, "Fixed-fixed (stiff rigid mount) -- upper bound"),
    ]
    sens_rows = []
    for bf, interp in boundary_cases:
        f = spoke_mode_Hz(bf)
        print(f"{bf:>18.1f}  {interp:<40}  {f:>14.1f}")
        sens_rows.append({
            "boundary_factor": bf,
            "interpretation":   interp,
            "f_spoke_Hz":       round(f, 2),
        })
    print()

    # Plot: modes overlaid on launch random-vib spectrum
    fig, ax = plt.subplots(figsize=(10, 5.5))
    f_grid = np.logspace(math.log10(10), math.log10(2500), 400)
    # Stylized launch PSD profile (NASA payload general envelope)
    psd = np.where(
        f_grid < 20.0, 0.005,
        np.where(
            f_grid < 50.0, 0.005 + (0.04 - 0.005) * (f_grid - 20) / 30,
            np.where(
                f_grid < 800.0, 0.04,
                np.maximum(0.005, 0.04 * (800 / f_grid) ** 1.5),
            ),
        ),
    )
    ax.plot(f_grid, psd, color="black", linewidth=2,
            label="Typical launch PSD envelope")
    ax.fill_between(f_grid, 0, psd, color="gray", alpha=0.15)

    for label, f in modes:
        if f is None or f > 2500 or f < 10:
            continue
        color = "tab:red" if 50 <= f <= 800 else "tab:blue"
        # locate PSD value at this f for the marker
        psd_at_f = np.interp(f, f_grid, psd)
        ax.axvline(f, color=color, linestyle=":", alpha=0.7)
        ax.scatter([f], [psd_at_f], color=color, s=60, zorder=5)
        ax.annotate(
            f"{label.split('(')[0].strip()[:24]}\n{f:.0f} Hz",
            xy=(f, psd_at_f), xytext=(5, 8),
            textcoords="offset points",
            fontsize=8, color=color, ha="left", va="bottom",
        )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(10, 2500)
    ax.set_ylim(1e-4, 0.2)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("PSD (g²/Hz)")
    ax.set_title("AURORA-Mono — estimated modes on a typical launch PSD\n"
                 "(red = inside the 50-800 Hz damaging band)")
    ax.grid(True, which="both", linestyle="--", alpha=0.4)
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    fig.savefig("plots/modal_on_launch_spectrum.png", dpi=120)
    print("Wrote plots/modal_on_launch_spectrum.png")

    # CSV outputs
    pd.DataFrame(rows).to_csv(
        "modal_analysis_summary.csv", index=False
    )
    pd.DataFrame(sens_rows).to_csv(
        "modal_analysis_suspension_sensitivity.csv", index=False
    )
    print("Wrote modal_analysis_summary.csv")
    print("Wrote modal_analysis_suspension_sensitivity.csv")
    print()

    # Verdict
    print("=" * 64)
    print("VERDICT")
    print("=" * 64)
    print()
    in_band_count = sum(1 for r in rows if r["in_50_800_Hz_band"])
    print(f"{in_band_count} of {len(rows)} estimated modes fall inside the "
          f"50-800 Hz launch-spectrum peak band.")
    print()
    if in_band_count == 0:
        v = ("All wheel modes are outside the damaging band of the "
             "launch spectrum. Resonant amplification at launch is "
             "unlikely to be a concern.")
    elif in_band_count <= 2:
        v = ("A subset of wheel modes sits inside the 50-800 Hz launch "
             "band. Miles' SDOF response gives moderate equivalent "
             "G-loads at these modes. Coupled-loads analysis with the "
             "rover/launch-vehicle is recommended to confirm whether "
             "the wheel can survive launch in this configuration.")
    else:
        v = ("Multiple wheel modes sit inside the 50-800 Hz launch "
             "spectrum peak band. The SDOF Miles' approximation under-"
             "estimates the cumulative response across modes. 3D random-"
             "vibration FEM or coupled-loads analysis is REQUIRED before "
             "this design can be cleared for launch.")
    print(v)
    print()
    print("Key insight: the rim's first ring mode (n=2 ovalization) is")
    print(f"estimated at {f_ring2:.0f} Hz -- well inside the launch-spectrum")
    print("peak. The spoke-bending mode varies from ~15 Hz (free spokes)")
    print(f"to ~{f_spoke_clamped:.0f} Hz (stiff mount); realistic suspension")
    print("boundary conditions will set the true value somewhere in between.")
    print()
    print("This is closed-form modal screening, NOT a 3D eigenanalysis.")
    print("Coupled-loads analysis with the rover suspension stays the actual")
    print("next-fidelity step.")


if __name__ == "__main__":
    main()
