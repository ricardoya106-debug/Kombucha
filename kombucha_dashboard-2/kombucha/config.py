"""
Central configuration for the kombucha digital twin project.
Tune these values as you calibrate against your own batches -- the numbers
here are reasonable starting points, not measured constants.
"""

# ---------- First fermentation (F1) ----------
F1_WEIGHTS = {
    "pH": 0.45,
    "conductivity": 0.35,
    # Temperature is intentionally NOT in this sum -- it modulates the FPI
    # afterward via temperature_factor() in normalization.py, multiplicatively
    # rather than additively. Weights below sum to less than 1.0 on purpose,
    # leaving headroom for that multiplier.
}
F1_IDEAL_TEMP_C = 27.0
F1_TEMP_SIGMA = 3.8
F1_D_MAX_DAYS = 12.0
F1_TOO_COLD_C = 25.0
F1_TOO_HOT_C = 29.0
F1_PH_STALL_THRESHOLD = 4.0
F1_PH_STALL_DAYS = 3.0  # warn if pH still above threshold after this many days

# ---------- Second fermentation (F2) ----------
F2_WEIGHTS = {
    "pressure": 0.60,
    # Same as F1: temperature modulates the FPI multiplicatively via
    # temperature_factor(), not as another additive term here.
}
F2_IDEAL_TEMP_C = 22.0
F2_TEMP_SIGMA = 3.5
F2_D_MAX_DAYS = 8.5
F2_PRESSURE_RISE_LIMIT_BAR_PER_DAY = 0.6  # above this -> over-carbonation risk
F2_PRESSURE_STALL_BAR = 0.3  # below this after several days -> low activity

# ---------- Shared ----------
EPSILON = 1e-9
DB_PATH = "kombucha_history.db"
SERIAL_BAUD_RATE = 9600