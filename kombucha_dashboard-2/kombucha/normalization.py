"""
Normalization and Fermentation Progress Index (FPI) calculations.

Every sensor is squashed to 0..1, where 1 means "closer to fully fermented".
Temperature is deliberately kept OUT of that weighted sum -- it acts as a
multiplier (temp_factor) that dampens the index when the brew is running
too cold or too hot, rather than as another additive term.
"""

import math
from . import config


def normalize(value, s_min, s_max, invert=False):
    """Min-max normalize a single reading to [0, 1] given batch/training bounds."""
    span = (s_max - s_min) + config.EPSILON
    norm = (value - s_min) / span
    norm = min(max(norm, 0.0), 1.0)
    return 1.0 - norm if invert else norm


def temperature_factor(temp_c, ideal_temp, sigma):
    """
    Gaussian falloff around the ideal fermentation temperature, remapped to
    stay in roughly [0.65, 1.0] so it dampens -- never zeroes out -- the FPI.
    """
    temp_eff = math.exp(-((temp_c - ideal_temp) ** 2) / (2 * sigma ** 2))
    return 0.65 + 0.35 * temp_eff, temp_eff


def temp_adjust_multiplier(temp_c, ideal_temp, too_cold, too_hot):
    """
    Multiplier on days-remaining: too cold stretches the estimate, too hot
    compresses it (fermentation runs faster but risks off-flavors).
    """
    if temp_c < too_cold:
        return 1.15
    if temp_c > too_hot:
        return 0.85
    return 1.0


def f1_fpi(pH, conductivity, temp_c, bounds):
    """
    bounds: dict with (min, max) for each sensor, e.g.
        {"pH": (3.0, 4.3), "conductivity": (200, 1400)}
    Returns every intermediate value so the dashboard can show its work,
    not just the final FPI.
    """
    pH_n = normalize(pH, *bounds["pH"], invert=True)
    cond_n = normalize(conductivity, *bounds["conductivity"], invert=False)

    raw_fpi = (
        config.F1_WEIGHTS["pH"] * pH_n
        + config.F1_WEIGHTS["conductivity"] * cond_n
    )

    t_factor, t_eff = temperature_factor(temp_c, config.F1_IDEAL_TEMP_C, config.F1_TEMP_SIGMA)
    fpi = raw_fpi * t_factor

    t_adjust = temp_adjust_multiplier(
        temp_c, config.F1_IDEAL_TEMP_C, config.F1_TOO_COLD_C, config.F1_TOO_HOT_C
    )
    days_remaining = max(0.0, config.F1_D_MAX_DAYS * (1 - fpi) * t_adjust)
    progress_pct = 100.0 * (1 - days_remaining / config.F1_D_MAX_DAYS)

    return {
        "pH_n": pH_n,
        "cond_n": cond_n,
        "raw_fpi": raw_fpi,
        "temp_eff": t_eff,
        "temp_factor": t_factor,
        "fpi": fpi,
        "temp_adjust": t_adjust,
        "days_remaining": days_remaining,
        "progress_pct": max(0.0, min(100.0, progress_pct)),
    }


def f2_fpi(pressure, temp_c, bounds):
    """
    bounds: dict with (min, max) for pressure, e.g.
        {"pressure": (0.0, 3.5)}
    """
    pressure_n = normalize(pressure, *bounds["pressure"], invert=False)

    raw_fpi = config.F2_WEIGHTS["pressure"] * pressure_n

    t_factor, t_eff = temperature_factor(temp_c, config.F2_IDEAL_TEMP_C, config.F2_TEMP_SIGMA)
    fpi = raw_fpi * t_factor

    t_adjust = temp_adjust_multiplier(
        temp_c,
        config.F2_IDEAL_TEMP_C,
        config.F2_IDEAL_TEMP_C - 3,
        config.F2_IDEAL_TEMP_C + 3,
    )
    days_remaining = max(0.0, config.F2_D_MAX_DAYS * (1 - fpi) * t_adjust)
    progress_pct = 100.0 * (1 - days_remaining / config.F2_D_MAX_DAYS)

    return {
        "pressure_n": pressure_n,
        "raw_fpi": raw_fpi,
        "temp_eff": t_eff,
        "temp_factor": t_factor,
        "fpi": fpi,
        "temp_adjust": t_adjust,
        "days_remaining": days_remaining,
        "progress_pct": max(0.0, min(100.0, progress_pct)),
    }