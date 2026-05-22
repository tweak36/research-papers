
"""
AURORA-Mono first-order screening model.

Important limitations:
- Not finite element analysis.
- Not a validated lunar wheel wear test.
- Thermal input is a prescribed temperature cycle, not a radiation/conduction simulation.
- Wear uses a simplified Archard-style law with estimated coefficients.
- Structural check is a local strip-stress screening calculation, not fracture mechanics.
"""

import math, numpy as np, pandas as pd

np.random.seed(7)
IN = 0.0254
distance_km = 1000.0
segment_m = 20.0
N = int(distance_km * 1000 / segment_m)

OD_in, width_in = 18.0, 8.0
R_outer = (OD_in / 2) * IN
width = width_in * IN

g_moon = 1.62
rover_mass_kg = 45.0
payload_mass_kg = 270.0
static_load_per_wheel_N = (rover_mass_kg + payload_mass_kg) * g_moon / 4.0
dynamic_spike_factor = 4.0

tread_hardness_Pa = 0.45e9
skin_allowable_stress_Pa = 160e6
wear_k_warm = 1.8e-4
wear_k_cold = 3.8e-4

temp_schedule_C_hours = [(-170, 6), (-100, 6), (-40, 3), (0, 2), (60, 1)]
speed_profile_kmh = [24, 18, 12, 8, 6]
speed_profile_mps = [v / 3.6 for v in speed_profile_kmh]
avg_segment_time_s = segment_m / np.mean(speed_profile_mps)
segments_per_hour = 3600 / avg_segment_time_s
temp_list = []
for T_C, hours in temp_schedule_C_hours:
    temp_list += [T_C] * max(1, int(hours * segments_per_hour))
temp_list = (temp_list * int(math.ceil(N / len(temp_list))))[:N]

def wear_coeff_from_temp(T_C):
    if T_C <= -150:
        return wear_k_cold
    if T_C >= 60:
        return wear_k_warm
    alpha = (T_C + 150) / 210
    return wear_k_cold + (wear_k_warm - wear_k_cold) * alpha

terrain_types = np.array(["loose", "compact", "rocky"])
terrain_probs = np.array([0.60, 0.30, 0.10])
mu_available_map = {"loose": 0.55, "compact": 0.40, "rocky": 0.48}
required_mu_20deg = math.tan(math.radians(20))

rock_event_prob = 0.05
rock_size_fracs = np.array([0.0, 0.125, 0.25, 0.50])
rock_size_probs = np.array([0.60, 0.28, 0.10, 0.02])
side_impact_prob = 0.02

effective_strip_width_m = 0.010
skin_thickness_m = 0.0012
effective_skin_area_m2 = effective_strip_width_m * skin_thickness_m

lug_coverage = 0.20
instant_contact_fraction = 0.20
surface_area_m2 = 2 * math.pi * R_outer * width
contact_area_m2 = surface_area_m2 * lug_coverage * instant_contact_fraction

records = []
cum_wear_mm = 0.0
fracture_flags = 0
side_impacts = 0
rock_events = 0

for i in range(N):
    T_C = temp_list[i]
    terrain = np.random.choice(terrain_types, p=terrain_probs)
    speed_kmh = speed_profile_kmh[i % len(speed_profile_kmh)]
    slip = 0.10 if terrain == "loose" else 0.06
    load_N = static_load_per_wheel_N
    rock_frac = 0.0

    if np.random.rand() < rock_event_prob:
        rock_events += 1
        rock_frac = float(np.random.choice(rock_size_fracs, p=rock_size_probs))
        load_N = max(load_N, static_load_per_wheel_N * dynamic_spike_factor * (0.5 + rock_frac))

    side_impact = False
    if np.random.rand() < side_impact_prob:
        side_impacts += 1
        side_impact = True
        load_N *= 1.2

    local_stress_Pa = load_N / effective_skin_area_m2
    safety_factor = skin_allowable_stress_Pa / local_stress_Pa
    if safety_factor < 1.0:
        fracture_flags += 1

    k = wear_coeff_from_temp(T_C)
    sliding_m = segment_m * (1 + slip)
    wear_volume_m3 = k * load_N * sliding_m / tread_hardness_Pa
    wear_depth_m = wear_volume_m3 / contact_area_m2
    cum_wear_mm += wear_depth_m * 1000

    avail_mu = mu_available_map[terrain]
    records.append({
        "segment": i,
        "distance_km": (i + 1) * segment_m / 1000,
        "temperature_C": T_C,
        "terrain": terrain,
        "speed_kmh": speed_kmh,
        "load_N": load_N,
        "rock_fraction_D": rock_frac,
        "side_impact": side_impact,
        "local_stress_MPa": local_stress_Pa / 1e6,
        "safety_factor": safety_factor,
        "cumulative_wear_mm": cum_wear_mm,
        "available_mu": avail_mu,
        "required_mu_20deg": required_mu_20deg,
        "traction_margin": avail_mu - required_mu_20deg,
    })

df = pd.DataFrame(records)
summary = pd.DataFrame([{
    "distance_km": distance_km,
    "static_load_per_wheel_N": static_load_per_wheel_N,
    "max_load_N_seen": df["load_N"].max(),
    "rock_events_count": rock_events,
    "side_impacts_count": side_impacts,
    "fracture_flags_SF_lt_1": fracture_flags,
    "minimum_safety_factor": df["safety_factor"].min(),
    "final_wear_mm": df["cumulative_wear_mm"].iloc[-1],
    "median_traction_margin_mu": df["traction_margin"].median(),
    "minimum_traction_margin_mu": df["traction_margin"].min(),
}])
df.to_csv("aurora_mono_screening_records.csv", index=False)
summary.to_csv("aurora_mono_screening_summary.csv", index=False)
