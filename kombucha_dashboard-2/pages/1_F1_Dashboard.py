"""
First fermentation (F1) dashboard.

Two separate data streams, on purpose:
- "Live sensor" polls every ~5 seconds and is used ONLY to run anomaly
  checks in near real time. It is never written to the database.
- "Logged" readings are written to SQLite -- and are what the graphs, FPI,
  and History page use -- on the interval set in the sidebar (1-30 min).
"""

import datetime as dt

import pandas as pd
import plotly.express as px
import streamlit as st

from kombucha import alerts, config, serial_reader, storage, theme
from kombucha.normalization import f1_fpi

st.set_page_config(page_title="F1 Dashboard", layout="wide")
theme.theme_picker()
st.title("First fermentation (F1)")

DEFAULT_BOUNDS = {
    "pH": (3.0, 4.3),
    "conductivity": (200, 1400),
}

LIVE_TICK_SECONDS = 5

# ---------------- Sidebar: data source ----------------
st.sidebar.header("Data source")
use_sim = st.sidebar.checkbox(
    "Use simulated readings", value=True,
    help="Turn off once your Arduino is wired up and streaming CSV lines over serial.",
)
port = st.sidebar.text_input("Serial port", value="/dev/ttyUSB0", disabled=use_sim)

# ---------------- Sidebar: batch controls ----------------
st.sidebar.header("Batch")
if "f1_batch" not in st.session_state:
    existing_max = storage.next_batch_number("F1") - 1
    st.session_state.f1_batch = existing_max if existing_max >= 1 else 1
if "f1_start_time" not in st.session_state:
    st.session_state.f1_start_time = dt.datetime.now()

if st.sidebar.button("Start new F1 batch"):
    st.session_state.f1_batch = storage.next_batch_number("F1")
    st.session_state.f1_start_time = dt.datetime.now()
    st.session_state.f1_mock_state = None
    st.session_state.f1_last_log_time = None
    st.session_state.f1_live_reading = None

batch = st.sidebar.number_input("Active batch #", min_value=1, value=int(st.session_state.f1_batch), step=1)
st.session_state.f1_batch = batch

# ---------------- Sidebar: logging interval ----------------
st.sidebar.header("Logging")
interval_min = st.sidebar.slider("Log interval (minutes)", 1, 30, 20)
manual_log = st.sidebar.button("Log a reading now")

# ---------------- Drive the 5-second live tick ----------------
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=LIVE_TICK_SECONDS * 1000, key="f1_live_autorefresh")
    autorefresh_available = True
except ImportError:
    autorefresh_available = False
    st.sidebar.caption(
        "Install `streamlit-autorefresh` for the live monitor and logging "
        "timer to update on their own; otherwise refresh the page manually."
    )

for key, default in [
    ("f1_last_log_time", None),
    ("f1_live_reading", None),
    ("f1_mock_state", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

now = dt.datetime.now()


def _get_reading():
    if use_sim:
        r = serial_reader.read_mock("F1", st.session_state.f1_mock_state)
        st.session_state.f1_mock_state = r
        return r
    try:
        return serial_reader.read_live(port, config.SERIAL_BAUD_RATE, serial_reader.F1_FIELDS)
    except RuntimeError as e:
        st.sidebar.error(str(e))
        return None


live_reading = _get_reading()
if live_reading:
    st.session_state.f1_live_reading = live_reading

# ---------------- Logging gate: only every interval_min minutes ----------------
auto_due = st.session_state.f1_last_log_time is None or (
    (now - st.session_state.f1_last_log_time).total_seconds() >= interval_min * 60
)
should_log = (manual_log or auto_due) and st.session_state.f1_live_reading is not None

if should_log:
    day = (now - st.session_state.f1_start_time).total_seconds() / 86400
    row = {
        "process": "F1", "source": "sim" if use_sim else "live",
        "batch": int(batch), "day": day,
        "recorded_at": now.isoformat(),
        **st.session_state.f1_live_reading,
    }
    storage.insert_reading(row)
    st.session_state.f1_last_log_time = now

# ---------------- Countdown to next logged reading ----------------
if st.session_state.f1_last_log_time:
    remaining = max(0, interval_min * 60 - (now - st.session_state.f1_last_log_time).total_seconds())
else:
    remaining = 0
mm, ss = divmod(int(remaining), 60)
st.sidebar.metric("Next logged reading in", f"{mm:02d}:{ss:02d}")

# ---------------- Live sensor panel (read every 5s, never saved) ----------------
st.subheader("Live sensor")
st.caption("Updates every ~5 seconds. Used only to watch for anomalies -- not saved to history or plotted below.")

if st.session_state.f1_live_reading:
    lr = st.session_state.f1_live_reading
    lc1, lc2, lc3 = st.columns(3)
    lc1.metric("pH (live)", f"{lr['pH']:.2f}")
    lc2.metric("Conductivity (live)", f"{lr['conductivity']:.0f}")
    lc3.metric("Temperature (live)", f"{lr['temperature_C']:.1f} C")

    live_day = (now - st.session_state.f1_start_time).total_seconds() / 86400
    live_alerts = alerts.f1_alerts(lr, live_day)
    if live_alerts:
        for level, msg in live_alerts:
            (st.error if level == "danger" else st.warning)(msg)
    else:
        st.success("No anomalies detected right now.")
else:
    st.info("Waiting for the first live reading...")

# ---------------- Load LOGGED history for graphs + FPI ----------------
hist = storage.load_history(process="F1", batch=int(batch))

if hist.empty:
    st.warning("No readings logged yet for this batch. One will log automatically, or click 'Log a reading now'.")
    st.stop()

latest = hist.iloc[-1]
day_elapsed = float(latest["day"])
bounds = DEFAULT_BOUNDS

result = f1_fpi(latest["pH"], latest["conductivity"], latest["temperature_C"], bounds)

st.subheader("Logged progress")
c1, c2, c3, c4 = st.columns(4)
c1.metric("FPI", f"{result['fpi']:.2f}")
c2.metric("Progress", f"{result['progress_pct']:.0f}%")
c3.metric("Est. days remaining", f"{result['days_remaining']:.1f}")
c4.metric("Batch day", f"{day_elapsed:.1f}")
st.progress(min(max(result["progress_pct"] / 100, 0.0), 1.0))

st.subheader("Sensor trends (logged data)")
hist["timestamp"] = pd.to_datetime(hist["recorded_at"])
sensor_cols = ["pH", "conductivity", "temperature_C"]
tabs = st.tabs(sensor_cols)
for tab, col in zip(tabs, sensor_cols):
    with tab:
        fig = px.line(hist, x="timestamp", y=col, markers=True, title=f"{col} vs. time")
        fig.update_xaxes(tickformat="%b %d, %H:%M", tickangle=45)
        st.plotly_chart(fig, use_container_width=True)

with st.expander("Raw FPI breakdown"):
    st.json({k: (round(v, 4) if isinstance(v, float) else v) for k, v in result.items()})
