"""
Second fermentation (F2) dashboard.
"""

import datetime as dt

import pandas as pd
import plotly.express as px
import streamlit as st

from kombucha import alerts, config, serial_reader, storage
from kombucha.normalization import f2_fpi

st.set_page_config(page_title="F2 Dashboard", layout="wide")
st.title("Second fermentation (F2)")

DEFAULT_BOUNDS = {
    "pressure": (0.0, 3.5),
}

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

batch = st.sidebar.number_input("Active batch #", min_value=1, value=int(st.session_state.f2_batch), step=1)
st.session_state.f2_batch = batch

# ---------------- Sidebar: polling ----------------
st.sidebar.header("Polling")
try:
    from streamlit_autorefresh import st_autorefresh
    autorefresh_available = True
except ImportError:
    autorefresh_available = False
    st.sidebar.caption("Install `streamlit-autorefresh` to poll automatically; using a manual button for now.")

interval_min = st.sidebar.slider("Log interval (minutes)", 1, 30, 20)
if autorefresh_available:
    st_autorefresh(interval=60_000, key="f2_autorefresh")

manual_log = st.sidebar.button("Log a reading now")

# ---------------- Time-gated logging ----------------
if "f2_last_log_time" not in st.session_state:
    st.session_state.f2_last_log_time = None

now = dt.datetime.now()
auto_due = autorefresh_available and (
    st.session_state.f2_last_log_time is None
    or (now - st.session_state.f2_last_log_time).total_seconds() >= interval_min * 60
)
log_now = manual_log or auto_due

if log_now:
    if use_sim:
        reading = serial_reader.read_mock("F2", st.session_state.get("f2_mock_state"))
        st.session_state.f2_mock_state = reading
    else:
        reading = None
        try:
            reading = serial_reader.read_live(port, config.SERIAL_BAUD_RATE, serial_reader.F2_FIELDS)
        except RuntimeError as e:
            st.sidebar.error(str(e))

    if reading:
        day = (now - st.session_state.f2_start_time).total_seconds() / 86400
        row = {
            "process": "F2",
            "source": "sim" if use_sim else "live",
            "batch": int(batch),
            "day": day,
            "recorded_at": now.isoformat(),
            **reading,
        }
        storage.insert_reading(row)
        st.session_state.f2_last_log_time = now
    elif not use_sim:
        st.sidebar.error("No reading received from the Arduino — check the port and baud rate.")

# ---------------- Load this batch's history ----------------
hist = storage.load_history(process="F2", batch=int(batch))

if hist.empty:
    st.warning("No readings logged yet for this batch. Use the sidebar to log one.")
    st.stop()

latest = hist.iloc[-1]
day_elapsed = float(latest["day"])
bounds = DEFAULT_BOUNDS

result = f2_fpi(
    latest["pressure_bar"],
    latest["temperature_C"],
    bounds,
)

# ---------------- Top metrics ----------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("FPI", f"{result['fpi']:.2f}")
c2.metric("Progress", f"{result['progress_pct']:.0f}%")
c3.metric("Est. days remaining", f"{result['days_remaining']:.1f}")
c4.metric("Batch day", f"{day_elapsed:.1f}")
st.progress(min(max(result["progress_pct"] / 100, 0.0), 1.0))

# ---------------- Alerts ----------------
st.subheader("Status")
pressure_history = list(zip(hist["day"].tolist(), hist["pressure_bar"].tolist()))
batch_alerts = alerts.f2_alerts(latest, day_elapsed, pressure_history)
if batch_alerts:
    for level, msg in batch_alerts:
        (st.error if level == "danger" else st.warning)(msg)
else:
    st.success("No anomalies detected for this batch.")

# ---------------- Per-sensor graphs ----------------
st.subheader("Sensor trends")

hist["timestamp"] = pd.to_datetime(hist["recorded_at"])

sensor_cols = ["pressure_bar", "temperature_C"]
tabs = st.tabs(sensor_cols)
for tab, col in zip(tabs, sensor_cols):
    with tab:
        fig = px.line(
            hist,
            x="timestamp",
            y=col,
            markers=True,
            title=f"{col} vs. time",
        )
        fig.update_xaxes(
            tickformat="%H:%M",
            tickangle=45,
        )
        st.plotly_chart(fig, use_container_width=True)

with st.expander("Raw FPI breakdown"):
    st.json({k: (round(v, 4) if isinstance(v, float) else v) for k, v in result.items()})