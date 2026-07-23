"""
Second fermentation (F2) dashboard.

Same split as F1: a 5-second live tick drives anomaly detection only,
while a separately time-gated logging step (1-30 min, set in the sidebar)
is what actually gets written to SQLite and shown in the graphs/History.
"""

import datetime as dt

import pandas as pd
import plotly.express as px
import streamlit as st

from kombucha import alerts, config, serial_reader, storage, theme
from kombucha.normalization import f2_fpi

st.set_page_config(page_title="F2 Dashboard", layout="wide")
theme.theme_picker()
st.title("Second fermentation (F2)")

DEFAULT_BOUNDS = {
    "pressure": (0.0, 3.5),
}

LIVE_TICK_SECONDS = 5
LIVE_BUFFER_MAX = 60  # ~5 min of live readings at a 5s tick, used only for rise-rate detection

# ---------------- Sidebar: data source ----------------
st.sidebar.header("Data source")
use_sim = st.sidebar.checkbox(
    "Use simulated readings", value=True,
    help="Turn off once your Arduino is wired up and streaming CSV lines over serial.",
)
port = st.sidebar.text_input("Serial port", value="/dev/ttyUSB1", disabled=use_sim)

# ---------------- Sidebar: batch controls ----------------
st.sidebar.header("Batch")
if "f2_batch" not in st.session_state:
    existing_max = storage.next_batch_number("F2") - 1
    st.session_state.f2_batch = existing_max if existing_max >= 1 else 1
if "f2_start_time" not in st.session_state:
    st.session_state.f2_start_time = dt.datetime.now()

if st.sidebar.button("Start new F2 batch"):
    st.session_state.f2_batch = storage.next_batch_number("F2")
    st.session_state.f2_start_time = dt.datetime.now()
    st.session_state.f2_mock_state = None
    st.session_state.f2_last_log_time = None
    st.session_state.f2_live_reading = None
    st.session_state.f2_live_buffer = []

batch = st.sidebar.number_input("Active batch #", min_value=1, value=int(st.session_state.f2_batch), step=1)
st.session_state.f2_batch = batch

# ---------------- Sidebar: logging interval ----------------
st.sidebar.header("Logging")
interval_min = st.sidebar.slider("Log interval (minutes)", 1, 30, 20)
manual_log = st.sidebar.button("Log a reading now")

# ---------------- Drive the 5-second live tick ----------------
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=LIVE_TICK_SECONDS * 1000, key="f2_live_autorefresh")
    autorefresh_available = True
except ImportError:
    autorefresh_available = False
    st.sidebar.caption(
        "Install `streamlit-autorefresh` for the live monitor and logging "
        "timer to update on their own; otherwise refresh the page manually."
    )

for key, default in [
    ("f2_last_log_time", None),
    ("f2_live_reading", None),
    ("f2_mock_state", None),
    ("f2_live_buffer", []),
]:
    if key not in st.session_state:
        st.session_state[key] = default

now = dt.datetime.now()


def _get_reading():
    if use_sim:
        r = serial_reader.read_mock("F2", st.session_state.f2_mock_state)
        st.session_state.f2_mock_state = r
        return r
    try:
        return serial_reader.read_live(port, config.SERIAL_BAUD_RATE, serial_reader.F2_FIELDS)
    except RuntimeError as e:
        st.sidebar.error(str(e))
        return None


live_reading = _get_reading()
live_day = (now - st.session_state.f2_start_time).total_seconds() / 86400
if live_reading:
    st.session_state.f2_live_reading = live_reading
    st.session_state.f2_live_buffer.append((live_day, live_reading["pressure_bar"]))
    st.session_state.f2_live_buffer = st.session_state.f2_live_buffer[-LIVE_BUFFER_MAX:]

# ---------------- Logging gate: only every interval_min minutes ----------------
auto_due = st.session_state.f2_last_log_time is None or (
    (now - st.session_state.f2_last_log_time).total_seconds() >= interval_min * 60
)
should_log = (manual_log or auto_due) and st.session_state.f2_live_reading is not None

if should_log:
    day = (now - st.session_state.f2_start_time).total_seconds() / 86400
    row = {
        "process": "F2", "source": "sim" if use_sim else "live",
        "batch": int(batch), "day": day,
        "recorded_at": now.isoformat(),
        **st.session_state.f2_live_reading,
    }
    storage.insert_reading(row)
    st.session_state.f2_last_log_time = now

# ---------------- Countdown to next logged reading ----------------
if st.session_state.f2_last_log_time:
    remaining = max(0, interval_min * 60 - (now - st.session_state.f2_last_log_time).total_seconds())
else:
    remaining = 0
mm, ss = divmod(int(remaining), 60)
st.sidebar.metric("Next logged reading in", f"{mm:02d}:{ss:02d}")

# ---------------- Live sensor panel (read every 5s, never saved) ----------------
st.subheader("Live sensor")
st.caption("Updates every ~5 seconds. Used only to watch for anomalies -- not saved to history or plotted below.")

if st.session_state.f2_live_reading:
    lr = st.session_state.f2_live_reading
    lc1, lc2 = st.columns(2)
    lc1.metric("Pressure (live)", f"{lr['pressure_bar']:.2f} bar")
    lc2.metric("Temperature (live)", f"{lr['temperature_C']:.1f} C")

    live_alerts = alerts.f2_alerts(lr, live_day, st.session_state.f2_live_buffer)
    if live_alerts:
        for level, msg in live_alerts:
            (st.error if level == "danger" else st.warning)(msg)
    else:
        st.success("No anomalies detected right now.")
else:
    st.info("Waiting for the first live reading...")

# ---------------- Load LOGGED history for graphs + FPI ----------------
hist = storage.load_history(process="F2", batch=int(batch))

if hist.empty:
    st.warning("No readings logged yet for this batch. One will log automatically, or click 'Log a reading now'.")
    st.stop()

latest = hist.iloc[-1]
day_elapsed = float(latest["day"])
bounds = DEFAULT_BOUNDS

result = f2_fpi(latest["pressure_bar"], latest["temperature_C"], bounds)

st.subheader("Logged progress")
c1, c2, c3, c4 = st.columns(4)
c1.metric("FPI", f"{result['fpi']:.2f}")
c2.metric("Progress", f"{result['progress_pct']:.0f}%")
c3.metric("Est. days remaining", f"{result['days_remaining']:.1f}")
c4.metric("Batch day", f"{day_elapsed:.1f}")
st.progress(min(max(result["progress_pct"] / 100, 0.0), 1.0))

st.subheader("Sensor trends (logged data)")
hist["timestamp"] = pd.to_datetime(hist["recorded_at"])
sensor_cols = ["pressure_bar", "temperature_C"]
tabs = st.tabs(sensor_cols)
for tab, col in zip(tabs, sensor_cols):
    with tab:
        fig = px.line(hist, x="timestamp", y=col, markers=True, title=f"{col} vs. time")
        fig.update_xaxes(tickformat="%b %d, %H:%M", tickangle=45)
        st.plotly_chart(fig, use_container_width=True)

with st.expander("Raw FPI breakdown"):
    st.json({k: (round(v, 4) if isinstance(v, float) else v) for k, v in result.items()})
