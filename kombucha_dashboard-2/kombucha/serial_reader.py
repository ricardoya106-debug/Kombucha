"""
Arduino serial reader, with a mock fallback so the dashboard runs (and is
demoable) even without hardware attached.

Real mode expects the Arduino to print one CSV line per reading over serial,
e.g. for F1:  4.02,410.5,26.8
matching F1_FIELDS order below. Adjust FIELD ORDER to match your own sketch's
Serial.println format -- this is the one place you'll likely need to edit
once you know exactly what your Arduino sends.
"""

import random

try:
    import serial  # pyserial
    PYSERIAL_AVAILABLE = True
except ImportError:
    PYSERIAL_AVAILABLE = False

F1_FIELDS = ["pH", "conductivity", "temperature_C"]
F2_FIELDS = ["pressure_bar", "temperature_C"]


def read_live(port, baud_rate, fields, timeout=2.0, warmup_reads=2):
    """Reads and parses one CSV line from the Arduino. Returns a dict or None."""
    if not PYSERIAL_AVAILABLE:
        raise RuntimeError("pyserial is not installed. Run: pip install pyserial")

    ser = serial.Serial(port, baud_rate, timeout=timeout)
    try:
        ser.reset_input_buffer()
        for _ in range(warmup_reads):
            ser.readline()
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if not line:
            return None
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != len(fields):
            return None
        try:
            return {f: float(v) for f, v in zip(fields, parts)}
        except ValueError:
            return None
    finally:
        ser.close()


def read_mock(process="F1", state=None):
    """
    Generates one plausible-looking reading, drifting slightly from the
    previous call, so you can build/demo the dashboard without hardware.
    Pass the previous return value back in as `state` to keep the walk
    continuous across calls.
    """
    if process == "F1":
        prev = state or {
            "pH": 4.1,
            "conductivity": 280,
            "temperature_C": 27,
        }
        reading = {
            "pH": max(3.0, prev["pH"] - random.uniform(0, 0.01)),
            "conductivity": prev["conductivity"] + random.uniform(0, 6),
            "temperature_C": 27 + random.uniform(-1, 1),
        }
    else:  # F2
        prev = state or {
            "pressure_bar": 0.1,
            "temperature_C": 22,
        }
        reading = {
            "pressure_bar": prev["pressure_bar"] + random.uniform(0, 0.03),
            "temperature_C": 22 + random.uniform(-1, 1),
        }
    return reading