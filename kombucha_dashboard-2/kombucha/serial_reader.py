"""
Arduino serial reader, with a mock fallback.
Uses a persistent connection so the Arduino does not reset on every read.
"""

import random
import time

try:
    import serial
    PYSERIAL_AVAILABLE = True
except ImportError:
    PYSERIAL_AVAILABLE = False

# The Arduino sketch outputs these 4 fields in this exact order
COMBINED_FIELDS = ["pH", "conductivity", "temperature_C", "pressure_bar"]

# Dashboard aliases
F1_FIELDS = COMBINED_FIELDS
F2_FIELDS = COMBINED_FIELDS

_active_connection = None
_active_port = None
_active_baud = None

def _get_connection(port, baud_rate, timeout):
    """Manages a singleton serial connection to prevent Arduino reboots."""
    global _active_connection, _active_port, _active_baud
    
    if not PYSERIAL_AVAILABLE:
        raise RuntimeError("pyserial is not installed. Run: pip install pyserial")

    # If port or baud changes, close the old connection
    if _active_connection is not None:
        if port != _active_port or baud_rate != _active_baud:
            _active_connection.close()
            _active_connection = None
        elif not _active_connection.is_open:
            _active_connection = None
            
    # Open a new connection if none exists
    if _active_connection is None:
        _active_connection = serial.Serial(port, baud_rate, timeout=timeout)
        _active_port = port
        _active_baud = baud_rate
        time.sleep(2)  # Allow Arduino DTR reset to settle
        _active_connection.reset_input_buffer()
        
    return _active_connection

def read_live(port, baud_rate, fields=None, timeout=2.0):
    """
    Reads the unified CSV line and returns a dict mapping all combined fields.
    The dashboards can just extract the keys they care about.
    """
    conn = _get_connection(port, baud_rate, timeout)
    
    # Flush older data so we always grab the freshest reading on the tick
    conn.reset_input_buffer() 
    line = conn.readline().decode("utf-8", errors="ignore").strip()
    
    if not line:
        return None
        
    parts = [p.strip() for p in line.split(",")]
    if len(parts) != len(COMBINED_FIELDS):
        return None
        
    try:
        return {f: float(v) for f, v in zip(COMBINED_FIELDS, parts)}
    except ValueError:
        return None

def read_mock(process="F1", state=None):
    if process == "F1":
        prev = state or {"pH": 4.1, "conductivity": 280, "temperature_C": 27}
        return {
            "pH": max(3.0, prev["pH"] - random.uniform(0, 0.01)),
            "conductivity": prev["conductivity"] + random.uniform(0, 6),
            "temperature_C": 27 + random.uniform(-1, 1),
        }
    else:  
        prev = state or {"pressure_bar": 0.1, "temperature_C": 22}
        return {
            "pressure_bar": prev["pressure_bar"] + random.uniform(0, 0.03),
            "temperature_C": 22 + random.uniform(-1, 1),
        }