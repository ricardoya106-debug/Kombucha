"""
Model performance: compares the hand-built FPI-derived days-remaining
against the learned regression model, both validated with leave-one-batch-
out cross validation.
"""

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.metrics import mean_absolute_error, r2_score

from kombucha import models, storage
from kombucha.data_sim import simulate_batches
from kombucha.normalization import f1_fpi, f2_fpi

st.set_page_config(page_title="Model Performance", layout="wide")
st.title("Model performance: FPI formula vs. regression")

DEFAULT_BOUNDS_F1 = {"pH": (3.0, 4.3), "conductivity": (200, 1400), "turbidity": (5, 120), "color": (0, 100)}
DEFAULT_BOUNDS_F2 = {"pressure": (0.0, 3.5), "water_level": (60, 100)}

process = st.selectbox("Process", ["F1", "F2"])
n_sim = st.slider(
    "Synthetic batches to blend in for training", 0, 30, 15,
    help="Real batches alone are usually too few to train a regression model reliably early on — "
         "blend in synthetic batches, then lean more on real ones as you accumulate them.",
)

real_all = storage.load_history(process=process, source="live")

completed_batches = []
if not real_all.empty:
    completed_batches = st.multiselect(
        "Which real batches are finished? (needed to know true days-remaining — "
        "in-progress batches are excluded from training/validation)",
        options=sorted(real_all["batch"].unique()),
    )

real = real_all[real_all["batch"].isin(completed_batches)].copy() if completed_batches else pd.DataFrame()
if not real.empty:
    real["actual_days_remaining"] = real.groupby("batch")["day"].transform("max") - real["day"]

sim = simulate_batches(process=process, n_batches=n_sim)
if not sim.empty and not real.empty:
    sim["batch"] = sim["batch"] + int(real["batch"].max()) + 1  # keep batch numbers distinct

combined = pd.concat([real, sim], ignore_index=True) if not sim.empty else real

if combined.empty:
    st.warning(
        "No labeled data available yet. Mark at least one real batch as finished above, "
        "or blend in synthetic batches with the slider."
    )
    st.stop()

if process == "F1":
    feat = models.build_feature_frame_f1(combined, DEFAULT_BOUNDS_F1)
    feature_cols = models.F1_FEATURES
    fpi_days_pred = combined.apply(
        lambda r: f1_fpi(r["pH"], r["conductivity"], r["turbidity"], r["color"], r["temperature_C"], DEFAULT_BOUNDS_F1)["days_remaining"],
        axis=1,
    )
else:
    feat = models.build_feature_frame_f2(combined, DEFAULT_BOUNDS_F2)
    feature_cols = models.F2_FEATURES
    fpi_days_pred = combined.apply(
        lambda r: f2_fpi(r["pressure_bar"], r["water_level_pct"], r["temperature_C"], DEFAULT_BOUNDS_F2)["days_remaining"],
        axis=1,
    )

model, fold_df, overall = models.train_and_validate(feat, feature_cols)

actual = combined["actual_days_remaining"].values
fpi_rmse = float(np.sqrt(np.mean((actual - fpi_days_pred.values) ** 2)))
fpi_mae = mean_absolute_error(actual, fpi_days_pred)
fpi_r2 = r2_score(actual, fpi_days_pred)

st.subheader("Overall (all batches pooled)")
comp = pd.DataFrame(
    {
        "RMSE (days)": [fpi_rmse, overall["rmse"]],
        "MAE (days)": [fpi_mae, overall["mae"]],
        "R2": [fpi_r2, overall["r2"]],
    },
    index=["Hand-built FPI formula", "Regression model (leave-one-batch-out)"],
)
st.dataframe(comp.style.format("{:.3f}"))

st.subheader("Per-batch validation (regression model)")
st.caption("R2 gets noisy with only a few batches — check whether error is spread evenly or driven by one outlier batch.")
if not fold_df.empty:
    st.dataframe(fold_df.style.format({"rmse": "{:.2f}", "mae": "{:.2f}", "r2": "{:.2f}"}))
else:
    st.info("Need at least 2 batches to run leave-one-batch-out validation.")

if st.button("Save trained regression model to disk"):
    path = f"{process.lower()}_regression_model.joblib"
    models.save_model(model, path)
    st.success(f"Saved to {path}")
