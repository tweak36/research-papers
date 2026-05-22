
"""
Viscoelastic relaxation screening upgrade to the thermal-cycle check.

NOT A FINITE ELEMENT ANALYSIS. This is a 1D lumped-parameter Prony-series
relaxation model with Arrhenius time-temperature superposition. It
addresses the dominant missing physics in `thermal_cycle_check.py` --
that PEKK creeps at +127 C during the long lunar-day dwell -- by
time-stepping the constrained-thermal stress through a multi-cycle
diurnal profile and allowing it to relax through a generalized Maxwell
material model.

What this DOES capture (and the elastic check does not):
- Stress decay during hot dwell from creep / relaxation
- Asymmetric stress cycle (fast cool-down builds stress, slow hot-dwell
  relaxes it) -> reduced stress amplitude per cycle
- Sensitivity to material relaxation parameters

What this does NOT capture:
- Geometry discretization. Real FEM would resolve edge stresses, lug
  geometry, and 3D stress states properly.
- Through-thickness gradients in the sandwich wall.
- Strain-rate sensitivity beyond Prony relaxation.
- Coupling between damage and time-temperature response.
- Actual measured Prony coefficients for the specific SiC-PEKK and
  PEKK-CNT/CF formulations. Coefficients here are educated estimates
  based on published PEEK/PEKK relaxation behavior.
- Mean-stress effect on fatigue (Goodman / Soderberg correction). The
  relaxed cycle is asymmetric (0 to peak) which is more damaging than a
  fully-reversed (-peak to +peak) cycle of the same amplitude; this
  screening uses Δσ/2 as amplitude without R-ratio correction.

This script is the right next-fidelity step IN PURE PYTHON. The real
next step beyond this is true 3D viscoelastic FEM with measured Prony
coefficients (still item on the open-work list).
"""

import math
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# Material model
# ============================================================

# Tread modulus (SiC-PEKK), glassy
E_TREAD_GLASSY_PA = 5.0e9

# CTE mismatch (from thermal_cycle_check.py)
ALPHA_TREAD = 29.0e-6
ALPHA_SKIN = 10.0e-6
DELTA_ALPHA = ALPHA_TREAD - ALPHA_SKIN  # 19e-6 K^-1

# Prony series for PEKK stress-relaxation modulus at the reference
# temperature. Estimated from published PEEK/PEKK behavior --
# below Tg there is a permanent rubbery plateau (~50% of glassy) and
# several relaxation processes between ~1e3 and ~1e6 seconds.
#
# E(t) / E_glassy = sum_i  w_i * exp(-t / tau_i)
PRONY_REF_TEMP_K = 400.0  # +127 C, the lunar hot temperature
PRONY = [
    # (weight w_i, relaxation time tau_i in seconds at reference T)
    (0.50, 1.0e15),  # permanent term (effectively infinite tau)
    (0.20, 1.0e3),   # fast relaxation, ~minutes
    (0.20, 1.0e5),   # intermediate, ~1 day
    (0.10, 1.0e6),   # slow, ~12 days
]
# Sanity: sum of weights = 1.0 (E(0)/E_glassy = 1)
assert abs(sum(w for w, _ in PRONY) - 1.0) < 1e-9


def shift_factor(temp_K, T_ref_K=PRONY_REF_TEMP_K, Ea_over_R=10000.0):
    """Arrhenius time-temperature shift factor a_T.

    a_T > 1 at temperatures above T_ref (relaxation faster: effective
    time passes more quickly).
    a_T < 1 below T_ref (relaxation slower: effective time slower).
    """
    if temp_K <= 0:
        return 1e-300
    log10_aT = (Ea_over_R / 2.302585) * (1.0 / T_ref_K - 1.0 / temp_K)
    # clip extreme values to keep math sane
    if log10_aT > 30:
        return 1e30
    if log10_aT < -30:
        return 1e-30
    return 10 ** log10_aT


def per_term_relaxation_factor(dt_s, temp_K, tau_i_s, Ea_over_R=10000.0):
    """Fraction of stress retained in one Prony Maxwell element over dt
    at temperature T. Uses TTS to find effective dt at the reference T,
    then exp(-dt_eff / tau_i)."""
    aT = shift_factor(temp_K, Ea_over_R=Ea_over_R)
    # effective time at reference T:
    dt_eff = dt_s * aT
    arg = dt_eff / tau_i_s
    if arg > 700:
        return 0.0
    return math.exp(-arg)


def step_viscoelastic(sigma_components, dt_s, dT_K, T_K,
                      E_glassy_Pa=E_TREAD_GLASSY_PA, dalpha=DELTA_ALPHA,
                      prony=PRONY, Ea_over_R=10000.0):
    """Advance the per-element stresses one time step.

    sigma_components: list of per-Maxwell-element stresses (MPa).
    dT_K: temperature change over this step (K). Positive = heating.
    T_K: current absolute temperature (K) used for relaxation.

    Convention: positive sigma means the tread is in tension (cool side).
    Cooling (dT<0) generates positive sigma_increment in the tread.
    """
    # Elastic stress increment per element, scaled by its glassy weight
    # so that sum of elements at zero relaxation equals the elastic
    # constrained-thermal stress
    d_sigma_total_MPa = -E_glassy_Pa * dalpha * dT_K / 1e6  # see convention
    new_components = []
    for sig_i, (w_i, tau_i) in zip(sigma_components, prony):
        # relax then add elastic increment scaled by w_i
        rf = per_term_relaxation_factor(dt_s, T_K, tau_i, Ea_over_R)
        sig_after = sig_i * rf + w_i * d_sigma_total_MPa
        new_components.append(sig_after)
    return new_components


# ============================================================
# Diurnal profile
# ============================================================

T_HOT_C = 127.0
T_COLD_C = -173.0

# Phase durations (Earth hours)
COOLDOWN_H = 24
COLD_DWELL_H = 14 * 24
HEATUP_H = 24
HOT_DWELL_H = 14 * 24
TOTAL_CYCLE_H = COOLDOWN_H + COLD_DWELL_H + HEATUP_H + HOT_DWELL_H

# Time-stepping
DT_TRANSIENT_S = 1800       # 30-min steps in cool-down / heat-up
DT_DWELL_HOT_S = 7200       # 2-h steps in hot dwell
DT_DWELL_COLD_S = 21600     # 6-h steps in cold dwell (slow relaxation)


def simulate_cycle(num_cycles=3, prony=PRONY, Ea_over_R=10000.0):
    """Time-step the bond stress through num_cycles diurnal cycles.

    Returns arrays (t_days, T_C, sigma_total_MPa).
    """
    sigma_components = [0.0 for _ in prony]
    t_s = 0.0
    times, temps, sigmas = [], [], []

    def add_point():
        times.append(t_s / 86400.0)
        temps.append(T_C_current)
        sigmas.append(sum(sigma_components))

    T_C_current = T_HOT_C  # start at end of a hot dwell (fully relaxed)
    add_point()

    for _ in range(num_cycles):
        # Cool-down: T_HOT -> T_COLD over COOLDOWN_H hours
        n_steps = int(COOLDOWN_H * 3600 / DT_TRANSIENT_S)
        dT_total = T_COLD_C - T_HOT_C
        dT_step = dT_total / n_steps
        for _ in range(n_steps):
            T_mid = T_C_current + 0.5 * dT_step
            T_K = T_mid + 273.15
            sigma_components = step_viscoelastic(
                sigma_components, DT_TRANSIENT_S, dT_step, T_K,
                prony=prony, Ea_over_R=Ea_over_R,
            )
            t_s += DT_TRANSIENT_S
            T_C_current += dT_step
            add_point()

        # Cold dwell (slow relaxation)
        n_steps = int(COLD_DWELL_H * 3600 / DT_DWELL_COLD_S)
        T_K = T_C_current + 273.15
        for _ in range(n_steps):
            sigma_components = step_viscoelastic(
                sigma_components, DT_DWELL_COLD_S, 0.0, T_K,
                prony=prony, Ea_over_R=Ea_over_R,
            )
            t_s += DT_DWELL_COLD_S
            add_point()

        # Heat-up: T_COLD -> T_HOT
        n_steps = int(HEATUP_H * 3600 / DT_TRANSIENT_S)
        dT_total = T_HOT_C - T_COLD_C
        dT_step = dT_total / n_steps
        for _ in range(n_steps):
            T_mid = T_C_current + 0.5 * dT_step
            T_K = T_mid + 273.15
            sigma_components = step_viscoelastic(
                sigma_components, DT_TRANSIENT_S, dT_step, T_K,
                prony=prony, Ea_over_R=Ea_over_R,
            )
            t_s += DT_TRANSIENT_S
            T_C_current += dT_step
            add_point()

        # Hot dwell (fast relaxation)
        n_steps = int(HOT_DWELL_H * 3600 / DT_DWELL_HOT_S)
        T_K = T_C_current + 273.15
        for _ in range(n_steps):
            sigma_components = step_viscoelastic(
                sigma_components, DT_DWELL_HOT_S, 0.0, T_K,
                prony=prony, Ea_over_R=Ea_over_R,
            )
            t_s += DT_DWELL_HOT_S
            add_point()

    return np.array(times), np.array(temps), np.array(sigmas)


# ============================================================
# Fatigue / SF math
# ============================================================

BOND_EFFECTIVE_PEEL_MPa = 10.0
BOND_ENDURANCE_RATIO = 0.25
BOND_ENDURANCE_LIMIT_MPa = BOND_EFFECTIVE_PEEL_MPa * BOND_ENDURANCE_RATIO
PEEL_RECOVERY = 0.40
CYCLES_PER_YEAR = 365.25 / 29.5


def basquin_sn_calibrate(sigma_static_MPa, R_e, endurance_cycles=1e6):
    sigma_endurance = sigma_static_MPa * R_e
    b = math.log10(endurance_cycles) / (sigma_static_MPa - sigma_endurance)
    a = b * sigma_static_MPa
    return a, b


def cycles_to_failure(sigma_MPa, a, b, endurance_limit_MPa):
    if sigma_MPa < endurance_limit_MPa:
        return float("inf")
    log_N = a - b * sigma_MPa
    if log_N < 0:
        return 0.5
    return 10 ** log_N


# ============================================================
# Main
# ============================================================

def analyze_cycle(times, temps, sigmas, last_cycle_only=True):
    """Compute interior max/min stress and amplitude from the simulated
    trace. Uses only the last cycle to avoid transients from initial
    conditions."""
    if last_cycle_only:
        cycle_days = TOTAL_CYCLE_H / 24.0
        mask = times >= (times.max() - cycle_days)
        s = sigmas[mask]
    else:
        s = sigmas
    s_max = float(np.max(s))
    s_min = float(np.min(s))
    s_range = s_max - s_min
    s_amplitude = s_range / 2.0
    return {
        "interior_max_MPa": s_max,
        "interior_min_MPa": s_min,
        "interior_range_MPa": s_range,
        "interior_amplitude_MPa": s_amplitude,
        "edge_max_MPa": s_max * PEEL_RECOVERY,
        "edge_amplitude_MPa": s_amplitude * PEEL_RECOVERY,
    }


def main():
    os.makedirs("plots", exist_ok=True)

    print("=" * 64)
    print("Viscoelastic relaxation screening (NOT FEM)")
    print("=" * 64)
    print(f"Prony series (relative to E_glassy = {E_TREAD_GLASSY_PA/1e9:.0f} GPa):")
    for w, tau in PRONY:
        if tau >= 1e10:
            tau_str = "infinite (permanent)"
        elif tau >= 86400:
            tau_str = f"{tau/86400:.2f} days"
        elif tau >= 3600:
            tau_str = f"{tau/3600:.1f} hours"
        elif tau >= 60:
            tau_str = f"{tau/60:.0f} min"
        else:
            tau_str = f"{tau:.0f} s"
        print(f"  w = {w:.2f}, tau = {tau:>22}  (at T_ref = "
              f"{PRONY_REF_TEMP_K-273.15:.0f} C)")
    print(f"Arrhenius Ea/R = 10000 K (typical thermoplastic temperature "
          f"sensitivity)")
    print()

    # === Run baseline simulation ===
    print("Simulating 3 diurnal cycles...")
    times, temps, sigmas = simulate_cycle(num_cycles=3)
    res = analyze_cycle(times, temps, sigmas)

    # Fatigue calc
    a, b = basquin_sn_calibrate(BOND_EFFECTIVE_PEEL_MPa, BOND_ENDURANCE_RATIO)
    # Use edge amplitude (×PEEL_RECOVERY) as the cyclic stress for the bond
    sigma_cyc_edge = res["edge_amplitude_MPa"]
    N_f = cycles_to_failure(sigma_cyc_edge, a, b, BOND_ENDURANCE_LIMIT_MPa)
    life_years = N_f / CYCLES_PER_YEAR if math.isfinite(N_f) else float("inf")

    sf_static_edge = (
        BOND_EFFECTIVE_PEEL_MPa / res["edge_max_MPa"]
        if res["edge_max_MPa"] > 0 else float("inf")
    )

    print(f"\nLast-cycle stress at the BOND interior (sum of Maxwell elements):")
    print(f"  Max     {res['interior_max_MPa']:>7.2f} MPa")
    print(f"  Min     {res['interior_min_MPa']:>7.2f} MPa")
    print(f"  Range   {res['interior_range_MPa']:>7.2f} MPa")
    print(f"  Amp     {res['interior_amplitude_MPa']:>7.2f} MPa")
    print(f"Estimated edge peel ({PEEL_RECOVERY:.1f} x interior):")
    print(f"  Max     {res['edge_max_MPa']:>7.2f} MPa  "
          f"(static SF vs {BOND_EFFECTIVE_PEEL_MPa:.0f} MPa allowable: "
          f"{sf_static_edge:.2f})")
    print(f"  Amp     {res['edge_amplitude_MPa']:>7.2f} MPa  "
          f"(vs endurance {BOND_ENDURANCE_LIMIT_MPa:.2f} MPa)")
    if math.isinf(N_f):
        print(f"  Fatigue cycles to failure:  infinite (below endurance)")
        print(f"  Fatigue life:               infinite")
    else:
        print(f"  Fatigue cycles to failure:  {N_f:.2g}")
        if life_years >= 1.0:
            print(f"  Fatigue life:               {life_years:.1f} years")
        else:
            print(f"  Fatigue life:               "
                  f"{life_years*365.25:.1f} days")
    print()

    # === Comparison vs elastic check ===
    elastic_interior = E_TREAD_GLASSY_PA * DELTA_ALPHA * 300.0 / 1e6
    elastic_edge = elastic_interior * PEEL_RECOVERY
    print("Comparison to the unrelaxed elastic check:")
    print(f"  Elastic constrained-thermal interior:  "
          f"{elastic_interior:>6.2f} MPa  (vs simulated max "
          f"{res['interior_max_MPa']:.2f} MPa)")
    print(f"  Elastic edge peel:                     "
          f"{elastic_edge:>6.2f} MPa  (vs simulated max "
          f"{res['edge_max_MPa']:.2f} MPa)")
    print(f"  Stress retention factor:               "
          f"{res['interior_max_MPa']/elastic_interior:>6.2f}")
    print()

    # === Save trace plot ===
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    ax = axes[0]
    ax.plot(times, temps, color="darkorange", linewidth=1.2)
    ax.set_ylabel("Temperature (°C)")
    ax.set_title("AURORA-Mono — viscoelastic bond stress over 3 lunar "
                 "diurnal cycles")
    ax.grid(True, linestyle="--", alpha=0.4)

    ax = axes[1]
    ax.plot(times, sigmas, color="steelblue", linewidth=1.2,
            label="Interior bond stress (Prony total)")
    edge_trace = np.array(sigmas) * PEEL_RECOVERY
    ax.plot(times, edge_trace, color="firebrick", linewidth=1.0,
            linestyle="--",
            label=f"Estimated edge peel (×{PEEL_RECOVERY:.1f})")
    ax.axhline(BOND_EFFECTIVE_PEEL_MPa, color="black", linestyle=":",
               alpha=0.6,
               label=f"Bond allowable ({BOND_EFFECTIVE_PEEL_MPa:.0f} MPa)")
    ax.axhline(BOND_ENDURANCE_LIMIT_MPa, color="red", linestyle=":",
               alpha=0.6,
               label=f"Bond endurance "
                     f"({BOND_ENDURANCE_LIMIT_MPa:.2f} MPa)")
    ax.axhline(-BOND_EFFECTIVE_PEEL_MPa, color="black", linestyle=":",
               alpha=0.6)
    ax.axhline(-BOND_ENDURANCE_LIMIT_MPa, color="red", linestyle=":",
               alpha=0.6)
    ax.set_xlabel("Time (Earth days)")
    ax.set_ylabel("Stress (MPa)")
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    fig.savefig("plots/viscoelastic_stress_trace.png", dpi=120)
    print("Wrote plots/viscoelastic_stress_trace.png")

    # === Sensitivity sweep on Ea/R and permanent-term weight ===
    print("\nSensitivity sweep on Arrhenius Ea/R and permanent-term weight:")
    print(f"{'Ea/R':>8}  {'w_inf':>7}  {'edge max':>10}  {'edge amp':>10}  "
          f"{'static SF':>10}  {'fatigue life':>14}")
    print("-" * 76)
    sens_rows = []
    for Ea_over_R in (6000, 10000, 15000):
        for w_inf in (0.30, 0.50, 0.70):
            # rescale Prony so sum = 1 with the new permanent weight
            other_weight = 1.0 - w_inf
            scaled = [(other_weight * w / (1.0 - PRONY[0][0]), tau)
                      for w, tau in PRONY[1:]]
            new_prony = [(w_inf, PRONY[0][1])] + scaled
            assert abs(sum(w for w, _ in new_prony) - 1.0) < 1e-9
            t, T, s = simulate_cycle(num_cycles=3, prony=new_prony,
                                     Ea_over_R=Ea_over_R)
            r = analyze_cycle(t, T, s)
            edge_max = r["edge_max_MPa"]
            edge_amp = r["edge_amplitude_MPa"]
            sf = (
                BOND_EFFECTIVE_PEEL_MPa / edge_max
                if edge_max > 0 else float("inf")
            )
            Nf = cycles_to_failure(edge_amp, a, b, BOND_ENDURANCE_LIMIT_MPa)
            life_y = (
                Nf / CYCLES_PER_YEAR if math.isfinite(Nf) else float("inf")
            )
            sf_str = "inf" if math.isinf(sf) else f"{sf:.2f}"
            life_str = (
                "inf" if math.isinf(life_y)
                else (f"{life_y:.1f} y" if life_y >= 1
                      else f"{life_y*365.25:.1f} d")
            )
            print(f"{Ea_over_R:>8.0f}  {w_inf:>7.2f}  "
                  f"{edge_max:>8.2f} MPa  {edge_amp:>8.2f} MPa  "
                  f"{sf_str:>10}  {life_str:>14}")
            sens_rows.append({
                "Ea_over_R_K": Ea_over_R,
                "permanent_term_weight": w_inf,
                "edge_max_MPa": round(edge_max, 3),
                "edge_amplitude_MPa": round(edge_amp, 3),
                "static_SF": (
                    None if math.isinf(sf) else round(sf, 3)
                ),
                "fatigue_life_years": (
                    None if math.isinf(life_y) else round(life_y, 3)
                ),
            })

    # === Save CSVs ===
    summary = {
        "E_tread_glassy_GPa": E_TREAD_GLASSY_PA / 1e9,
        "delta_alpha_ppm_per_K": DELTA_ALPHA * 1e6,
        "delta_T_full_K": 300.0,
        "Ea_over_R_K": 10000,
        "permanent_term_weight": PRONY[0][0],
        "elastic_interior_full_MPa": round(elastic_interior, 3),
        "elastic_edge_full_MPa": round(elastic_edge, 3),
        "viscoelastic_interior_max_MPa": round(res["interior_max_MPa"], 3),
        "viscoelastic_interior_amplitude_MPa": round(
            res["interior_amplitude_MPa"], 3
        ),
        "viscoelastic_edge_max_MPa": round(res["edge_max_MPa"], 3),
        "viscoelastic_edge_amplitude_MPa": round(
            res["edge_amplitude_MPa"], 3
        ),
        "stress_retention_factor": round(
            res["interior_max_MPa"] / elastic_interior, 4
        ),
        "static_SF_edge": (
            None if math.isinf(sf_static_edge) else round(sf_static_edge, 3)
        ),
        "fatigue_cycles_to_failure": (
            None if math.isinf(N_f) else round(N_f, 4)
        ),
        "fatigue_life_years": (
            None if math.isinf(life_years) else round(life_years, 3)
        ),
    }
    pd.DataFrame([summary]).to_csv(
        "viscoelastic_relaxation_summary.csv", index=False
    )
    pd.DataFrame(sens_rows).to_csv(
        "viscoelastic_relaxation_sensitivity.csv", index=False
    )
    print("\nWrote viscoelastic_relaxation_summary.csv")
    print("Wrote viscoelastic_relaxation_sensitivity.csv")
    print()

    # === Verdict ===
    print("=" * 64)
    print("VERDICT (honest)")
    print("=" * 64)
    print(f"Elastic constrained-thermal upper bound (from thermal_cycle_check):")
    print(f"  edge peel = {elastic_edge:.2f} MPa, static SF = "
          f"{BOND_EFFECTIVE_PEEL_MPa/elastic_edge:.2f}, "
          f"fatigue life ~15 days")
    print()
    print(f"Viscoelastic relaxation screening (this script):")
    print(f"  edge peel (max) = {res['edge_max_MPa']:.2f} MPa, "
          f"static SF = {sf_static_edge:.2f}")
    print(f"  edge amplitude = {res['edge_amplitude_MPa']:.2f} MPa, "
          f"fatigue life = ", end="")
    if math.isinf(life_years):
        print("infinite")
    elif life_years >= 1.0:
        print(f"{life_years:.1f} years")
    else:
        print(f"{life_years*365.25:.1f} days")
    print()
    if sf_static_edge >= 2.0:
        verdict = ("Crediting realistic viscoelastic relaxation moves the "
                   "thermal-cycle margin from a concern to a comfortable one.")
    elif sf_static_edge >= 1.0:
        verdict = ("Viscoelastic relaxation improves the margin but does not "
                   "fully resolve it. Real coupon-test Prony data and 3D FEM "
                   "are required to convict.")
    else:
        verdict = ("Even with viscoelastic relaxation, the margin remains "
                   "below 1.0. Design changes (compliant interlayer, "
                   "reduced CTE mismatch) are likely required regardless "
                   "of fidelity improvements in analysis.")
    print(verdict)
    print()
    print("This screening still does NOT replace true viscoelastic FEM with")
    print("measured Prony coefficients, which remains on the open-work list.")


if __name__ == "__main__":
    main()
