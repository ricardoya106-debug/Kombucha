"""
Synthetic batch generator.

Real fermentation data is expensive to collect (a batch takes days), so we
bootstrap the regression model with simulated batches that follow the same
kind of logistic/asymptotic curves real fermentation shows, with randomized
duration, temperature profile, and noise. Swap these out for real historical
batches as you accumulate them -- see storage.py and the model performance
page, which let you blend real + synthetic or use real batches only.
"""

import numpy as np
import pandas as pd


def _logistic(t, total_days, steepness=1.0, midpoint_frac=0.45):
    midpoint = total_days * midpoint_frac
    return 1.0 / (1.0 + np.exp(-steepness * (t - midpoint)))


def simulate_f1_batch(batch_id, total_days=None, readings_per_day=72, rng=None, ideal_temp=27.0):
    """readings_per_day=72 matches one reading every 20 minutes."""
    rng = rng or np.random.default_rng()
    total_days = total_days or rng.uniform(8, 14)
    n = max(int(total_days * readings_per_day), 2)
    t = np.linspace(0, total_days, n)

    progress = _logistic(t, total_days, steepness=rng.uniform(0.7, 1.1))

    temp = ideal_temp + rng.normal(0, 1.2, n) + rng.uniform(-1.5, 1.5)
    pH = 4.15 - 0.85 * progress + rng.normal(0, 0.03, n)
    conductivity = 250 + 900 * progress + rng.normal(0, 20, n)
    turbidity = 110 - 90 * progress + rng.normal(0, 4, n)
    color = 10 + 60 * progress + rng.normal(0, 2, n)
    water_level = 100 - 4 * (t / total_days) + rng.normal(0, 0.5, n)

    df = pd.DataFrame({
        "process": "F1", "source": "sim", "batch": batch_id,
        "day": t, "pH": pH, "conductivity": conductivity,
        "turbidity": turbidity, "color": color,
        "temperature_C": temp, "water_level_pct": water_level,
    })
    df["actual_days_remaining"] = np.clip(total_days - t, 0, None)
    return df


def simulate_f2_batch(batch_id, total_days=None, readings_per_day=72, rng=None, ideal_temp=22.0):
    rng = rng or np.random.default_rng()
    total_days = total_days or rng.uniform(4, 9)
    n = max(int(total_days * readings_per_day), 2)
    t = np.linspace(0, total_days, n)

    progress = _logistic(t, total_days, steepness=rng.uniform(0.8, 1.3))

    temp = ideal_temp + rng.normal(0, 1.0, n) + rng.uniform(-1.5, 1.5)
    pressure = 3.0 * progress + rng.normal(0, 0.05, n)
    water_level = 95 - 3 * (t / total_days) + rng.normal(0, 0.4, n)

    df = pd.DataFrame({
        "process": "F2", "source": "sim", "batch": batch_id,
        "day": t, "pressure_bar": pressure, "temperature_C": temp,
        "water_level_pct": water_level,
    })
    df["actual_days_remaining"] = np.clip(total_days - t, 0, None)
    return df


def simulate_batches(process="F1", n_batches=10, seed=42):
    if n_batches <= 0:
        return pd.DataFrame()
    rng = np.random.default_rng(seed)
    sim_fn = simulate_f1_batch if process == "F1" else simulate_f2_batch
    frames = [sim_fn(batch_id=i + 1, rng=rng) for i in range(n_batches)]
    return pd.concat(frames, ignore_index=True)
