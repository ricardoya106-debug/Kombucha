"""
Rule-based early-warning checks, layered on top of (not replacing) the FPI.
These catch a batch behaving abnormally for its current state, even if the
index still looks fine.
"""

from . import config


def f1_alerts(latest, batch_day):
    """
    latest: dict/Series with pH, conductivity, turbidity, temperature_C
    batch_day: days elapsed in this batch
    Returns a list of (level, message) tuples; level is 'warning' or 'danger'.
    """
    alerts = []
    temp = latest["temperature_C"]

    if temp < config.F1_TOO_COLD_C:
        alerts.append(("warning", f"Temperature {temp:.1f}C is below the ideal range; fermentation may be slowed."))
    elif temp > config.F1_TOO_HOT_C:
        alerts.append(("danger", f"Temperature {temp:.1f}C is above the ideal range; risk of off-flavors or a stressed culture."))

    if batch_day > config.F1_PH_STALL_DAYS and latest["pH"] > config.F1_PH_STALL_THRESHOLD:
        alerts.append((
            "warning",
            f"pH is still {latest['pH']:.2f} after {batch_day:.1f} days; acidification is slower than "
            "expected -- check temperature, starter tea ratio, or SCOBY health.",
        ))

    return alerts


def f2_alerts(latest, batch_day, pressure_history):
    """
    pressure_history: list of (day, pressure_bar) for this batch, oldest
    first, used to estimate the rise rate.
    """
    alerts = []
    temp = latest["temperature_C"]
    ideal = config.F2_IDEAL_TEMP_C

    if temp < ideal - 3:
        alerts.append(("warning", f"Temperature {temp:.1f}C is low; carbonation will build slowly."))
    elif temp > ideal + 3:
        alerts.append(("danger", f"Temperature {temp:.1f}C is high; risk of overpressure and off-flavors."))

    if len(pressure_history) >= 2:
        (d0, p0), (d1, p1) = pressure_history[-2], pressure_history[-1]
        dt = max(d1 - d0, 1e-6)
        rise_rate = (p1 - p0) / dt
        if rise_rate > config.F2_PRESSURE_RISE_LIMIT_BAR_PER_DAY:
            alerts.append((
                "danger",
                f"Pressure rising at {rise_rate:.2f} bar/day; risk of over-carbonation -- "
                "consider refrigerating or burping the bottles.",
            ))

    if batch_day > 3 and latest["pressure_bar"] < config.F2_PRESSURE_STALL_BAR:
        alerts.append(("warning", f"Pressure is only {latest['pressure_bar']:.2f} bar after {batch_day:.1f} days; possible low yeast activity."))

    return alerts
