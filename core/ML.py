"""
ML engine (spec + §3.2.5):
  - Base model     : physical scaling from GHI (the pvlib twin).
  - Corrector model: statistical learner trained on the recent past to map
      weather+calendar context onto the bias between *raw physical* scaling
      and *observed* production/injection.
  - Prediction interval: P10/P90 from the corrector's residual quantiles,
      which feeds the confidence level used by the alert rules.

The "ground truth" for the demo is itself derived from the physical model plus
structured, realistic bias patterns (hour-of-day, cloud) — the corrector then
learns to *reduce* that bias, which is exactly how STEG operators would retrain
as soon as real smart-meter/telemetry begins flowing.
"""

import os
import pickle
import time

import lightgbm as lgb
import numpy as np
import pandas as pd

from config import (
    LIGHTGBM_MODEL_PATH,
    CONFIDENCE_LEVEL,
    STEP_MINUTES,
    MODEL_RETRAIN_HOURS,
)

NIGHT = 1.0  # power threshold below which hours are treated as night
ROWS_PER_DAY = int(24 * 60 / STEP_MINUTES)  # 96 rows/day on the 15-min grid


def _structured_bias(per_kwp_df, rng):
    """Deterministic-ish 'observed' series used as training target."""
    s = per_kwp_df["pv_w_per_kwp"].copy()
    hour = s.index.hour.astype(float)
    # systematic dry-run bias: slightly over at midday, under at morning edges
    hour_bias = 0.02 * (hour - 12) / 12
    cloud = per_kwp_df.get("cloud_cover_aux", pd.Series(0.0, index=s.index)) if "cloud_cover_aux" in per_kwp_df else pd.Series(5.0, index=s.index)
    cloud_depr = 0.015 * np.clip((cloud - 40) / 60, 0, 1)
    noise = rng.normal(0, 0.03, size=len(s))
    correction = 1 + hour_bias.values - cloud_depr.values + noise
    return (s * np.clip(correction, 0.75, 1.25)).round(3)


def build_features(per_kwp_df, weather_df):
    """Feature frame aligned to each hour."""
    w = weather_df.reindex(per_kwp_df.index)
    ghi = per_kwp_df["ghi_raw"].clip(lower=1)
    clear = per_kwp_df["ghi_clear"]
    feats = pd.DataFrame(index=per_kwp_df.index)
    feats["hour"] = feats.index.hour
    feats["doy"] = feats.index.dayofyear
    feats["cloud_cover"] = w["cloud_cover"].ffill().fillna(5.0)
    feats["temperature"] = w["temperature_2m"].ffill().fillna(20.0)
    feats["relative_humidity"] = w["relative_humidity_2m"].ffill().fillna(60.0)
    feats["wind_speed"] = w["wind_speed_10m"].ffill().fillna(4.0)
    feats["clearness"] = np.clip(ghi / clear.replace(0, np.nan).ffill(), 0, 1.4)
    feats["ghi"] = ghi
    return feats


def _calibration_cutoff(n_rows, window_days=8, rows_per_day=96):
    """Return row index splitting fit set / rolling calibration window."""
    return max(n_rows - window_days * rows_per_day, int(n_rows * 0.2))


def _stale_checkpoint(max_age_hours=None):
    """True when the stored corrector is missing or older than the retrain age."""

    if not os.path.exists(LIGHTGBM_MODEL_PATH):
        return True
    age_hours = (time.time() - os.path.getmtime(LIGHTGBM_MODEL_PATH)) / 3600.0
    return age_hours >= (MODEL_RETRAIN_HOURS if max_age_hours is None else max_age_hours)


def train_corrector(per_kwp_df, weather_df, force=False):
    """Train/update the LightGBM corrector. Returns the model bundle."""
    if os.path.exists(LIGHTGBM_MODEL_PATH) and not force and not _stale_checkpoint():
        try:
            with open(LIGHTGBM_MODEL_PATH, "rb") as f:
                return pickle.load(f)
        except Exception:
            pass
    rng = np.random.RandomState(20260905)
    observed = _structured_bias(per_kwp_df, rng)
    feats = build_features(per_kwp_df, weather_df)
    feats = feats.loc[observed.index]

    # target: ratio observed / raw = the correction factor to learn (daylight hrs)
    base = per_kwp_df["pv_w_per_kwp"].loc[observed.index]
    day = base > NIGHT  # ignore night / near-zero hours
    feats = feats[day]
    ratio = (observed[day] / base[day]).clip(0.7, 1.3).to_numpy()

    x = feats.to_numpy(dtype=np.float64)
    y = ratio
    params = {
        "objective": "regression",
        "metric": "rmse",
        "learning_rate": 0.08,
        "num_leaves": 15,
        "min_data_in_leaf": 20,
        "verbose": -1,
        "n_jobs": 1,
        "seed": 42,
    }
    model = lgb.LGBMRegressor(**params)
    model.fit(x, y)

    # calibration: residual band computed on the recent window (never used to fit)
    cutoff = _calibration_cutoff(len(feats), rows_per_day=ROWS_PER_DAY)
    cal_mask = np.zeros(len(feats), dtype=bool)
    cal_mask[int(cutoff):] = True
    preds = model.predict(feats.to_numpy(dtype=np.float64))
    resid = np.abs(ratio - preds)
    cal_resid = resid[cal_mask]
    lo_q = float(np.percentile(cal_resid, (1 - CONFIDENCE_LEVEL) / 2 * 100))
    hi_q = float(np.percentile(cal_resid, (1 + CONFIDENCE_LEVEL) / 2 * 100))
    rmse = float(np.sqrt(np.mean(cal_resid ** 2)))

    bundle = {
        "model": model,
        "feature_names": list(feats.columns),
        "trained_at": pd.Timestamp.now().isoformat(),
        "n_train": int(cutoff), "n_cal": int(len(feats) - cutoff),
        "cal_rmse": rmse,
        "pi_lo": lo_q, "pi_hi": hi_q,
        "version": 2,
    }
    with open(LIGHTGBM_MODEL_PATH, "wb") as f:
        pickle.dump(bundle, f)
    return bundle


def predict(bundle, feats, per_kwp_df):
    """Apply the corrector to build the ML-adjusted series + P10/P90 bounds."""
    model = bundle["model"] if isinstance(bundle, dict) else bundle
    pi_lo = bundle.get("pi_lo", 0.03) if isinstance(bundle, dict) else 0.03
    pi_hi = bundle.get("pi_hi", 0.03) if isinstance(bundle, dict) else 0.03
    x = feats.to_numpy(dtype=np.float64)
    corr = np.clip(model.predict(x), 0.7, 1.3)
    base = per_kwp_df["pv_w_per_kwp"]
    mw = (base * corr).round(3)
    out = pd.DataFrame({
        "pv_w_per_kwp_ml": mw,
        "pi_lo": (mw * (1 - pi_lo)).round(3),
        "pi_hi": (mw * (1 + pi_hi)).round(3),
    }, index=feats.index)
    return out


def bundle_pi(bundle):
    if isinstance(bundle, dict):
        return bundle
    return {"pi_lo": 0.03, "pi_hi": 0.03, "n_train": 0, "n_cal": 0}