"""
Kombucha digital twin - home page.
Run with: streamlit run app.py
"""

import streamlit as st

from kombucha import theme

st.set_page_config(page_title="Kombucha digital twin", layout="wide")
theme.theme_picker()

st.title("Kombucha fermentation digital twin")
st.markdown(
    """
This app tracks first fermentation (F1) and second fermentation (F2) batches,
combines live Arduino sensor readings with a normalized Fermentation Progress
Index (FPI), and cross-checks that hand-built index against a regression
model trained on batch history.


**Use the sidebar to navigate:**
- **F1 Dashboard** — live pH, conductivity, temperature
- **F2 Dashboard** — live pressure, temperature
- **History** — every stored reading across all batches, filterable
- **Model Performance** — RMSE / MAE / R² for the FPI formula *and* the
  regression model, validated batch by batch
"""
)

st.info(
    "First time running this? Open the F1 or F2 page and leave "
    "**'Use simulated readings'** checked in the sidebar to try the "
    "dashboard without an Arduino connected."
)

with st.expander("Project notes / assumptions baked into this build"):
    st.markdown(
        """
- **Live sensor vs. logged data:** each dashboard polls a sensor reading
  every ~5 seconds purely to run anomaly checks in near real time. Only
  that reading is discarded -- it is never written to disk. A separate,
  time-gated step (interval set per-dashboard, 1-30 min) is what actually
  gets logged to SQLite and shown in the graphs, History, and Model
  Performance pages. If it isn't logged, it isn't saved.
- A sidebar countdown on each dashboard shows how long until the next
  logged reading.
- Pick a theme from the sidebar dropdown on any page; it carries over as
  you navigate. Alert colors stay consistent across all themes so severity
  always reads the same way.
- Readings are stored in a local SQLite file (`kombucha_history.db`) next to
  this app, so history survives a restart.
- Sensor min/max bounds used for normalization are set as reasonable
  defaults in each dashboard page — replace them with the actual observed
  range from your own batches once you have a few.
- The regression model needs *completed* batches to know the true
  "days remaining" label at each timestamp. The Model Performance page asks
  you which real batches are finished before using them for training.
- With only a handful of real batches, blend in synthetic batches (toggle
  on the Model Performance page) so the regression model has enough rows to
  fit without wildly overfitting — lean more on real batches as you collect
  them.
"""
    )