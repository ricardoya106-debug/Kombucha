"""
Regression model: learns to predict actual days remaining directly from
normalized sensor features. Upgraded with rate-of-change derivatives, 
tuned regularization (RidgeCV), and a Mixed-Effects model for structured data.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import statsmodels.formula.api as smf
import joblib

from .normalization import normalize, temperature_factor
from . import config

# Added derivative features
F1_FEATURES = ["pH_n", "cond_n", "temp_eff", "dpH_dt", "dcond_dt"]
F2_FEATURES = ["pressure_n", "temp_eff", "dpres_dt"]

def _add_rate_features(df, value_col, time_col, rate_col, window=3):
    """Calculates a rolling slope to capture the rate of change per batch."""
    df = df.sort_values(["batch", time_col])
    
    # Calculate rolling differences
    d_val = df.groupby("batch")[value_col].diff(periods=window)
    d_time = df.groupby("batch")[time_col].diff(periods=window)
    rate = d_val / (d_time + 1e-6)
    
    # Handle the warm-up period (fill NaNs with 1-period diff, then 0)
    rate_1pt = df.groupby("batch")[value_col].diff(periods=1) / (df.groupby("batch")[time_col].diff(periods=1) + 1e-6)
    rate = rate.fillna(rate_1pt).fillna(0)
    
    df[rate_col] = rate
    return df

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
        "pH": raw_df["pH"],
        "conductivity": raw_df["conductivity"],
        "day": raw_df["day"],
        "batch": raw_df["batch"].values,
        "actual_days_remaining": raw_df["actual_days_remaining"].values
    })
    
    feat = _add_rate_features(feat, "pH", "day", "dpH_dt")
    feat = _add_rate_features(feat, "conductivity", "day", "dcond_dt")
    return feat

def build_feature_frame_f2(raw_df, bounds):
    pressure_n = raw_df["pressure_bar"].apply(lambda v: normalize(v, *bounds["pressure"], invert=False))
    temp_eff = raw_df["temperature_C"].apply(
        lambda v: temperature_factor(v, config.F2_IDEAL_TEMP_C, config.F2_TEMP_SIGMA)[1]
    )
    feat = pd.DataFrame({
        "pressure_n": pressure_n,
        "temp_eff": temp_eff,
        "pressure": raw_df["pressure_bar"],
        "day": raw_df["day"],
        "batch": raw_df["batch"].values,
        "actual_days_remaining": raw_df["actual_days_remaining"].values
    })
    
    feat = _add_rate_features(feat, "pressure", "day", "dpres_dt")
    return feat

def _rmse(true, pred):
    return float(np.sqrt(mean_squared_error(true, pred)))

def train_and_validate(feature_df, feature_cols):
    """
    Leave-one-batch-out cross validation. Evaluates RidgeCV (tuned regularization)
    and MixedLM (Mixed-Effects modeling).
    """
    batches = sorted(feature_df["batch"].unique())
    fold_rows = []
    
    all_true = []
    all_pred_ridge = []
    all_pred_mixed = []

    # Grid search array for Ridge Alpha
    alphas = np.logspace(-3, 3, 20)

    for held_out in batches:
        train = feature_df[feature_df["batch"] != held_out]
        test = feature_df[feature_df["batch"] == held_out]
        
        if len(batches) < 2 or len(test) == 0 or len(train) == 0:
            continue

        true = test["actual_days_remaining"].values

        # 1. RidgeCV Training (Automatically tunes alpha)
        ridge_model = RidgeCV(alphas=alphas, store_cv_values=False)
        ridge_model.fit(train[feature_cols], train["actual_days_remaining"])
        pred_ridge = ridge_model.predict(test[feature_cols])
        
        # 2. Mixed-Effects Training 
        formula = "actual_days_remaining ~ " + " + ".join(feature_cols)
        try:
            mixed_model = smf.mixedlm(formula, train, groups=train["batch"]).fit(disp=False)
            pred_mixed = mixed_model.predict(test)
        except Exception:
            # Fallback to ridge if mixed model fails to converge mathematically
            pred_mixed = pred_ridge 

        fold_rows.append({
            "batch": held_out,
            "rmse_ridge": _rmse(true, pred_ridge),
            "rmse_mixed": _rmse(true, pred_mixed),
            "mae": mean_absolute_error(true, pred_ridge),
            "r2": r2_score(true, pred_ridge) if len(true) > 1 else np.nan,
            "n": len(true),
        })
        
        all_true.extend(true)
        all_pred_ridge.extend(pred_ridge)
        all_pred_mixed.extend(pred_mixed)

    fold_df = pd.DataFrame(fold_rows)
    
    if all_true:
        overall = {
            "rmse_ridge": _rmse(all_true, all_pred_ridge),
            "rmse_mixed": _rmse(all_true, all_pred_mixed),
            "mae": mean_absolute_error(all_true, all_pred_ridge),
            "r2": r2_score(all_true, all_pred_ridge),
        }
    else:
        overall = {"rmse_ridge": np.nan, "rmse_mixed": np.nan, "mae": np.nan, "r2": np.nan}

    # Fit final models on ALL data for actual usage
    final_ridge = RidgeCV(alphas=alphas)
    final_ridge.fit(feature_df[feature_cols], feature_df["actual_days_remaining"])

    return final_ridge, fold_df, overall

def save_model(model, path):
    joblib.dump(model, path)

def load_model(path):
    return joblib.load(path)