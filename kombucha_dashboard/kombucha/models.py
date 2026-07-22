"""
Regression model: learns to predict actual days remaining directly from
normalized sensor features, as a data-driven counterpart to the hand-built
FPI formula. Includes leave-one-batch-out cross validation, which matters
because each batch is a correlated time series, not an independent sample --
a random row-level train/test split would leak nearby timepoints from the
same batch into both sides and make the model look better than it is.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

from .normalization import normalize, temperature_factor
from . import config

F1_FEATURES = ["pH_n", "cond_n", "temp_eff"]
F2_FEATURES = ["pressure_n", "temp_eff"]


def build_feature_frame_f1(raw_df, bounds):
    pH_n = raw_df["pH"].apply(lambda v: normalize(v, *bounds["pH"], invert=True))
    cond_n = raw_df["conductivity"].apply(lambda v: normalize(v, *bounds["conductivity"], invert=False))
    temp_eff = raw_df["temperature_C"].apply(
        lambda v: temperature_factor(v, config.F1_IDEAL_TEMP_C, config.F1_TEMP_SIGMA)[1]
    )
    feat = pd.DataFrame({
        "pH_n": pH_n,
        "cond_n": cond_n,
        "temp_eff": temp_eff,
    })
    feat["batch"] = raw_df["batch"].values
    feat["actual_days_remaining"] = raw_df["actual_days_remaining"].values
    return feat


def build_feature_frame_f2(raw_df, bounds):
    pressure_n = raw_df["pressure_bar"].apply(lambda v: normalize(v, *bounds["pressure"], invert=False))
    temp_eff = raw_df["temperature_C"].apply(
        lambda v: temperature_factor(v, config.F2_IDEAL_TEMP_C, config.F2_TEMP_SIGMA)[1]
    )
    feat = pd.DataFrame({
        "pressure_n": pressure_n,
        "temp_eff": temp_eff,
    })
    feat["batch"] = raw_df["batch"].values
    feat["actual_days_remaining"] = raw_df["actual_days_remaining"].values
    return feat


def _rmse(true, pred):
    return float(np.sqrt(mean_squared_error(true, pred)))


def train_and_validate(feature_df, feature_cols, alpha=1.0):
    """
    Leave-one-batch-out cross validation. Returns the model fitted on ALL
    batches (for future predictions), a per-fold metrics table, and pooled
    overall metrics. Check the per-fold table before trusting the overall
    number -- with only a handful of batches, one unusual batch can swing
    R2 a lot.
    """
    batches = sorted(feature_df["batch"].unique())
    fold_rows = []
    all_true, all_pred = [], []

    for held_out in batches:
        train = feature_df[feature_df["batch"] != held_out]
        test = feature_df[feature_df["batch"] == held_out]
        if len(batches) < 2 or len(test) == 0 or len(train) == 0:
            continue

        model = Ridge(alpha=alpha)
        model.fit(train[feature_cols], train["actual_days_remaining"])
        pred = model.predict(test[feature_cols])
        true = test["actual_days_remaining"].values

        fold_rows.append({
            "batch": held_out,
            "rmse": _rmse(true, pred),
            "mae": mean_absolute_error(true, pred),
            "r2": r2_score(true, pred) if len(true) > 1 else np.nan,
            "n": len(true),
        })
        all_true.extend(true)
        all_pred.extend(pred)

    fold_df = pd.DataFrame(fold_rows)
    if all_true:
        overall = {
            "rmse": _rmse(all_true, all_pred),
            "mae": mean_absolute_error(all_true, all_pred),
            "r2": r2_score(all_true, all_pred),
        }
    else:
        overall = {"rmse": np.nan, "mae": np.nan, "r2": np.nan}

    final_model = Ridge(alpha=alpha)
    final_model.fit(feature_df[feature_cols], feature_df["actual_days_remaining"])

    return final_model, fold_df, overall


def save_model(model, path):
    joblib.dump(model, path)


def load_model(path):
    return joblib.load(path)