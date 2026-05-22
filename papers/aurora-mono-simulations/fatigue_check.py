
"""
Miner's-rule fatigue accumulator for the AURORA-Mono skin and lug-skin bond.

For each segment in the 1000 km screening mission, count the number of
wheel-rotation load cycles, look up the per-cycle stress, and accumulate
fatigue damage:

    D = sum_i  n_i / N_f(sigma_i)

Failure is conventionally taken at D = 1.0; design margin keeps D < 0.5
over the design life. The implied fatigue safety factor is 1/D and the
implied fatigue life is (design distance) / D.

S-N curves use a Basquin-style log-linear fit calibrated so that
N_f = 1 at the static strength and N_f = 1e6 at a representative
endurance limit. Stresses below the endurance limit contribute zero
damage (infinite-life assumption).

Skin (PEKK-CNT/CF):
  sigma_static = 160 MPa
  endurance ratio R_e = 0.40  -> endurance limit 64 MPa

Bond peel (effective allowable, conservative):
  sigma_static = 10 MPa  (5 MPa chemical x 2.0 key multiplier)
  endurance ratio R_e = 0.25  -> endurance limit 2.5 MPa
  Thermoplastic bonds have lower endurance ratios than the bulk material.

Stress per cycle:
  Skin   -> per-segment local_stress_MPa from the screening model
  Bond   -> per-segment peak peel stress computed from per-lug normal load
            and an assumed eccentric-load offset: L/4 for cruise, L/2 for
            rock events.

Limitations:
- S-N curves are generic thermoplastic estimates, NOT measured coupon
  data for PEKK-CNT/CF or the SiC-PEKK / PEKK co-mold bond.
- No mean-stress (Goodman / Soderberg) correction.
- No load-sequence interaction effects.
- 1 wheel rotation = 1 stress cycle; for rock events the segment's
  elevated stress is applied to all rotations in that segment (conservative
  -- real rock events are 1-3 cycles long, not a full segment).
- No thermal-cycling stress; differential CTE between SiC-PEKK and
  PEKK-CNT/CF would add diurnal-cycle damage not captured here.
"""

import math
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from aurora_mono_screening_model import run_screening

# --- Geometry ---
WHEEL_OD_M = 18.0 * 0.0254
WHEEL_CIRCUMFERENCE_M = math.pi * WHEEL_OD_M
SEGMENT_M = 20.0
CYCLES_PER_SEGMENT = SEGMENT_M / WHEEL_CIRCUMFERENCE_M  # ~14

LUG_LENGTH_M = 0.040
LUG_WIDTH_M = 0.014
LUGS_IN_CONTACT = 2

# --- S-N: skin ---
SKIN_STATIC_MPa = 160.0
SKIN_ENDURANCE_RATIO = 0.40
SKIN_ENDURANCE_LIMIT_MPa = SKIN_STATIC_MPa * SKIN_ENDURANCE_RATIO

# --- S-N: bond peel ---
BOND_CHEMICAL_MPa = 5.0
ANTI_PEEL_KEY_MULT = 2.0
BOND_PEEL_STATIC_MPa = BOND_CHEMICAL_MPa * ANTI_PEEL_KEY_MULT
BOND_ENDURANCE_RATIO = 0.25
BOND_PEEL_ENDURANCE_LIMIT_MPa = BOND_PEEL_STATIC_MPa * BOND_ENDURANCE_RATIO


def calibrate_sn(sigma_static_MPa, endurance_ratio, endurance_cycles=1e6):
    """Return (a, b) such that log10(N_f) = a - b * sigma_MPa."""
    sigma_endurance = sigma_static_MPa * endurance_ratio
    b = math.log10(endurance_cycles) / (sigma_static_MPa - sigma_endurance)
    a = b * sigma_static_MPa
    return a, b


def damage_per_segment(sigma_MPa_array, cycles_per_segment, a, b,
                       endurance_limit_MPa):
    """Vectorized per-segment damage.

    Cycles below the endurance limit contribute zero. Cycles above the
    static strength contribute 1.0 each (effectively instantaneous
    failure).
    """
    sigma = np.asarray(sigma_MPa_array, dtype=float)
    log_N = a - b * sigma
    N_f = np.where(log_N > 0, 10 ** log_N, 0.5)
    damage = cycles_per_segment / N_f
    damage = np.where(sigma < endurance_limit_MPa, 0.0, damage)
    return damage


def per_lug_peak_peel_MPa(load_per_lug_N, offset_m,
                          lug_width_m=LUG_WIDTH_M,
                          lug_length_m=LUG_LENGTH_M):
    """Peak peel stress at lug edge from eccentric normal load."""
    moment_Nm = load_per_lug_N * offset_m
    sigma_Pa = 6.0 * moment_Nm / (lug_width_m * lug_length_m ** 2)
    return sigma_Pa / 1e6


def event_breakdown(damage_array, df):
    rock_mask = (df["rock_fraction_D"].values > 0)
    side_mask = df["side_impact"].values & ~rock_mask
    cruise_mask = ~(rock_mask | side_mask)
    total = damage_array.sum()
    if total <= 0:
        return {"total": 0.0, "cruise": 0.0, "rock": 0.0, "side": 0.0,
                "cruise_pct": 0.0, "rock_pct": 0.0, "side_pct": 0.0}
    cruise_d = float(damage_array[cruise_mask].sum())
    rock_d = float(damage_array[rock_mask].sum())
    side_d = float(damage_array[side_mask].sum())
    return {
        "total": float(total),
        "cruise": cruise_d,
        "rock": rock_d,
        "side": side_d,
        "cruise_pct": cruise_d / total * 100,
        "rock_pct": rock_d / total * 100,
        "side_pct": side_d / total * 100,
    }


def format_life(life_km):
    if math.isinf(life_km):
        return "infinite (all cycles below endurance limit)"
    if life_km > 1e6:
        return f"{life_km/1e3:.0f},000 km"
    return f"{life_km:.0f} km"


def main():
    os.makedirs("plots", exist_ok=True)
    print("Running screening model to extract load history...")
    df, summary = run_screening()
    distance_km = float(summary["distance_km"])
    n_segments = len(df)
    total_cycles = CYCLES_PER_SEGMENT * n_segments

    # === Skin fatigue ===
    skin_a, skin_b = calibrate_sn(SKIN_STATIC_MPa, SKIN_ENDURANCE_RATIO)
    sigma_skin = df["local_stress_MPa"].values
    skin_damage = damage_per_segment(
        sigma_skin, CYCLES_PER_SEGMENT, skin_a, skin_b,
        SKIN_ENDURANCE_LIMIT_MPa,
    )
    skin = event_breakdown(skin_damage, df)
    skin_SF = (1.0 / skin["total"]) if skin["total"] > 0 else float("inf")
    skin_life_km = (
        distance_km / skin["total"] if skin["total"] > 0 else float("inf")
    )
    skin_cycles_above_endurance = int(
        np.sum(sigma_skin >= SKIN_ENDURANCE_LIMIT_MPa) * CYCLES_PER_SEGMENT
    )

    # === Bond peel fatigue ===
    bond_a, bond_b = calibrate_sn(BOND_PEEL_STATIC_MPa, BOND_ENDURANCE_RATIO)
    load_per_lug = df["load_N"].values / LUGS_IN_CONTACT
    offset = np.where(
        df["rock_fraction_D"].values > 0,
        LUG_LENGTH_M / 2.0,   # worst eccentric for rock events
        LUG_LENGTH_M / 4.0,   # moderate for cruise
    )
    sigma_peel = per_lug_peak_peel_MPa(load_per_lug, offset)
    bond_damage = damage_per_segment(
        sigma_peel, CYCLES_PER_SEGMENT, bond_a, bond_b,
        BOND_PEEL_ENDURANCE_LIMIT_MPa,
    )
    bond = event_breakdown(bond_damage, df)
    bond_SF = (1.0 / bond["total"]) if bond["total"] > 0 else float("inf")
    bond_life_km = (
        distance_km / bond["total"] if bond["total"] > 0 else float("inf")
    )
    bond_cycles_above_endurance = int(
        np.sum(sigma_peel >= BOND_PEEL_ENDURANCE_LIMIT_MPa) * CYCLES_PER_SEGMENT
    )

    # === Report ===
    print()
    print("=" * 64)
    print("Miner's-rule fatigue check (NOT measured S-N data)")
    print("=" * 64)
    print(f"Mission distance:        {distance_km:.0f} km")
    print(f"Wheel circumference:     {WHEEL_CIRCUMFERENCE_M*1000:.1f} mm")
    print(f"Cycles per segment:      {CYCLES_PER_SEGMENT:.2f}")
    print(f"Total stress cycles:     {total_cycles:,.0f}")
    print()
    print(f"SKIN  (PEKK-CNT/CF, sigma_static={SKIN_STATIC_MPa} MPa, "
          f"R_e={SKIN_ENDURANCE_RATIO}, endurance limit "
          f"{SKIN_ENDURANCE_LIMIT_MPa:.0f} MPa)")
    print(f"  Stress range observed: {sigma_skin.min():.1f} - "
          f"{sigma_skin.max():.1f} MPa")
    print(f"  Cycles above endurance: {skin_cycles_above_endurance:,}")
    print(f"  Total damage (D):      {skin['total']:.3e}")
    print(f"    Cruise:    {skin['cruise']:.3e} ({skin['cruise_pct']:5.1f}%)")
    print(f"    Rock event:{skin['rock']:.3e} ({skin['rock_pct']:5.1f}%)")
    print(f"    Side imp:  {skin['side']:.3e} ({skin['side_pct']:5.1f}%)")
    print(f"  Fatigue SF (1/D):      "
          f"{skin_SF:.1f}" if not math.isinf(skin_SF) else
          f"  Fatigue SF (1/D):      infinite")
    print(f"  Implied fatigue life:  {format_life(skin_life_km)}")
    print()
    print(f"BOND PEEL (effective allowable {BOND_PEEL_STATIC_MPa:.1f} MPa "
          f"= {BOND_CHEMICAL_MPa} chem * {ANTI_PEEL_KEY_MULT}x keys, "
          f"R_e={BOND_ENDURANCE_RATIO}, endurance limit "
          f"{BOND_PEEL_ENDURANCE_LIMIT_MPa:.2f} MPa)")
    print(f"  Stress range observed: {sigma_peel.min():.3f} - "
          f"{sigma_peel.max():.3f} MPa")
    print(f"  Cycles above endurance: {bond_cycles_above_endurance:,}")
    print(f"  Total damage (D):      {bond['total']:.3e}")
    print(f"    Cruise:    {bond['cruise']:.3e} ({bond['cruise_pct']:5.1f}%)")
    print(f"    Rock event:{bond['rock']:.3e} ({bond['rock_pct']:5.1f}%)")
    print(f"    Side imp:  {bond['side']:.3e} ({bond['side_pct']:5.1f}%)")
    if math.isinf(bond_SF):
        print(f"  Fatigue SF (1/D):      infinite")
    else:
        print(f"  Fatigue SF (1/D):      {bond_SF:.1f}")
    print(f"  Implied fatigue life:  {format_life(bond_life_km)}")
    print()

    # === Sensitivity: bond fatigue is the more interesting case because
    # the answer depends on whether we credit the anti-peel keys. Run a
    # small sensitivity grid on (chem allowable, key multiplier, endurance
    # ratio) ===
    print("Sensitivity sweep (BOND fatigue):")
    print(f"{'Chem MPa':>9} {'Key mult':>9} {'R_e':>5} "
          f"{'Static MPa':>11} {'Endur MPa':>10} {'D':>12} {'SF':>10} "
          f"{'Life (km)':>14}")
    print("-" * 86)
    sens_rows = []
    for chem in (3.0, 5.0, 7.0):
        for km in (1.0, 2.0, 3.0):
            for r_e in (0.20, 0.25, 0.30):
                sigma_static = chem * km
                endur = sigma_static * r_e
                a, b = calibrate_sn(sigma_static, r_e)
                d_arr = damage_per_segment(
                    sigma_peel, CYCLES_PER_SEGMENT, a, b, endur,
                )
                D = float(d_arr.sum())
                SF = (1.0 / D) if D > 0 else float("inf")
                life_km = distance_km / D if D > 0 else float("inf")
                sf_str = "inf" if math.isinf(SF) else f"{SF:.1f}"
                life_str = (
                    "inf" if math.isinf(life_km)
                    else (f"{life_km/1e3:.0f}e3" if life_km > 1e5
                          else f"{life_km:.0f}")
                )
                print(f"{chem:>9.1f} {km:>9.1f} {r_e:>5.2f} "
                      f"{sigma_static:>11.1f} {endur:>10.2f} "
                      f"{D:>12.2e} {sf_str:>10} {life_str:>14}")
                sens_rows.append({
                    "chemical_allowable_MPa": chem,
                    "key_multiplier": km,
                    "endurance_ratio": r_e,
                    "static_strength_MPa": sigma_static,
                    "endurance_limit_MPa": endur,
                    "total_damage": D,
                    "fatigue_SF": (None if math.isinf(SF) else round(SF, 2)),
                    "fatigue_life_km": (
                        None if math.isinf(life_km) else round(life_km, 1)
                    ),
                })
    print()

    # === Plot: stress histograms with endurance limit ===
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    ax = axes[0]
    ax.hist(sigma_skin, bins=40, color="steelblue", edgecolor="black",
            alpha=0.8)
    ax.axvline(SKIN_ENDURANCE_LIMIT_MPa, color="red", linestyle="--",
               linewidth=2,
               label=f"Endurance limit ({SKIN_ENDURANCE_LIMIT_MPa:.0f} MPa)")
    ax.axvline(SKIN_STATIC_MPa, color="black", linestyle=":", linewidth=2,
               label=f"Static strength ({SKIN_STATIC_MPa:.0f} MPa)")
    ax.set_xlabel("Skin local stress (MPa)")
    ax.set_ylabel("Segment count")
    ax.set_title("Skin stress histogram vs S-N thresholds")
    ax.set_yscale("log")
    ax.legend(fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.4)

    ax = axes[1]
    ax.hist(sigma_peel, bins=40, color="coral", edgecolor="black", alpha=0.8)
    ax.axvline(BOND_PEEL_ENDURANCE_LIMIT_MPa, color="red", linestyle="--",
               linewidth=2,
               label=f"Endurance limit "
                     f"({BOND_PEEL_ENDURANCE_LIMIT_MPa:.2f} MPa)")
    ax.axvline(BOND_PEEL_STATIC_MPa, color="black", linestyle=":", linewidth=2,
               label=f"Static allowable ({BOND_PEEL_STATIC_MPa:.1f} MPa)")
    ax.set_xlabel("Bond peak peel stress (MPa)")
    ax.set_ylabel("Segment count")
    ax.set_title("Bond peel stress histogram vs S-N thresholds")
    ax.set_yscale("log")
    ax.legend(fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.4)

    fig.tight_layout()
    fig.savefig("plots/fatigue_stress_histograms.png", dpi=120)
    print("Wrote plots/fatigue_stress_histograms.png")

    # === CSV outputs ===
    summary_row = {
        "distance_km": distance_km,
        "total_cycles": int(total_cycles),
        "skin_static_MPa": SKIN_STATIC_MPa,
        "skin_endurance_ratio": SKIN_ENDURANCE_RATIO,
        "skin_max_stress_MPa": round(float(sigma_skin.max()), 2),
        "skin_cycles_above_endurance": skin_cycles_above_endurance,
        "skin_total_damage": float(skin["total"]),
        "skin_fatigue_SF": (
            None if math.isinf(skin_SF) else round(skin_SF, 2)
        ),
        "skin_fatigue_life_km": (
            None if math.isinf(skin_life_km) else round(skin_life_km, 1)
        ),
        "bond_static_MPa": BOND_PEEL_STATIC_MPa,
        "bond_endurance_ratio": BOND_ENDURANCE_RATIO,
        "bond_max_peel_MPa": round(float(sigma_peel.max()), 4),
        "bond_cycles_above_endurance": bond_cycles_above_endurance,
        "bond_total_damage": float(bond["total"]),
        "bond_fatigue_SF": (
            None if math.isinf(bond_SF) else round(bond_SF, 2)
        ),
        "bond_fatigue_life_km": (
            None if math.isinf(bond_life_km) else round(bond_life_km, 1)
        ),
    }
    pd.DataFrame([summary_row]).to_csv("fatigue_check_summary.csv", index=False)
    pd.DataFrame(sens_rows).to_csv("fatigue_check_sensitivity.csv", index=False)
    print("Wrote fatigue_check_summary.csv")
    print("Wrote fatigue_check_sensitivity.csv")


if __name__ == "__main__":
    main()
