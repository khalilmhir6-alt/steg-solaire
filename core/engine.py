"""
Forecast engine: assembles weather + twin + ML into the scope-level
injection/demand view and detects ramp alerts (spec: -10% jaune / -20% rouge
sur 60 min), then persists a JSON payload for operator tools.
"""

import json
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from config import (
    STEP_MINUTES,
    RAMP_YELLOW_THRESHOLD,
    RAMP_RED_THRESHOLD,
    RAMP_WINDOW_MINUTES,
    CONFIDENCE_LEVEL,
    RESULT_PATH,
    ACTUAL_LOG_PATH,
    FORECAST_DAYS,
    FORECAST_DAYS_MAX,
    HORIZON_MIN_HOURS,
    HORIZON_MAX_HOURS,
    DEMAND_TEMP_REF_C,
    DEMAND_TEMP_COEF,
    DEMAND_WEEKEND_FACTOR,
    DEMAND_SEASON_FACTOR,
)
from core import weather, twin, ML
from ui import hierarchy




def _append_actual_records(fut_log, scope, scenario, horizon_hours):
    """Append-only capture of forecast vs measured production.

    Single storage change: one JSONL line per step appended to ACTUAL_LOG_PATH.
    Today every 'actual' value is SIMULATED (forecast + a small random walk)
    until a real metering stream is wired in — every record carries
    source='simulated' so operators can tell the two apart immediately.
    When the real meter exists, replace `actual_mw` below with the measured MW
    and drop the mock; the schema and the append writer stay the same.
    """
    if fut_log is None or len(fut_log) == 0:
        return

    rng = np.random.default_rng(seed=7)  # stable mock, otherwise the chart jumps
    recorded_at = pd.Timestamp.now(tz="Africa/Tunis").isoformat()
    lines = []
    for ts, row in fut_log.iterrows():
        forecast_mw = float(row["inject_ml_mw"]) if "inject_ml_mw" in fut_log.columns \
            else float(row.get("inject_phys_mw", 0.0))
        # measured MW: anchored on the REAL physics twin built from the actual
        # Open-Meteo window (real GHI + solar geometry on the installed fleet),
        # then a sky-dependent variation — the "actual" line follows real
        # weather-driven physics, staying close to the ML forecast by design.
        phys_mw = float(row.get("inject_phys_mw", 0.0))
        ghi_raw = float(row.get("ghi", 0.0))
        ghi_clear = float(row.get("ghi_clear", 0.0))
        cloud = float(row.get("cloud", 100.0))
        sun_ratio = (ghi_raw / ghi_clear) if ghi_clear > 20 else 0.0
        # sky type from the real GHI vs clear-sky ratio, then cloud as a tiebreak
        if sun_ratio >= 0.55:
            sky, sky_sigma = "clair", 0.008
        elif sun_ratio >= 0.30:
            sky, sky_sigma = "partiel", 0.025
        else:
            sky, sky_sigma = "nuageux", max(0.05, 0.08 * min(max(cloud, 0.0), 100.0) / 100.0)
        # night: GHI flat => measured equals the zeroed physical twin
        if ghi_raw <= 1.0:
            actual_mw = phys_mw
        else:
            actual_mw = phys_mw * (1.0 + rng.normal(0.0, sky_sigma))
        lines.append(json.dumps({
            "ts": ts.isoformat(),
            "scope": scope,
            "scenario": scenario,
            "horizon_hours": horizon_hours,
            "forecast_mw": round(forecast_mw, 3),
            "actual_mw": round(max(actual_mw, 0.0), 3),
            "sky": sky,
            "source": "simulated",
            "recorded_at": recorded_at,
        }, ensure_ascii=False))

    with open(ACTUAL_LOG_PATH, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def build_forecast(scope="tunisia", scenario=None, horizon_days=None,
                   horizon_hours=None, force_ml=False, force_weather=False,
                   allow_mock=True):
    """Full forecast pipeline for a scope. Returns a rich dict for the UI."""
    hours = horizon_hours if horizon_hours is not None else (horizon_days or FORECAST_DAYS) * 24
    hours = min(max(float(hours), HORIZON_MIN_HOURS), HORIZON_MAX_HOURS)
    wdf, wmeta = weather.fetch(force_refresh=force_weather, allow_mock=allow_mock)

    pk = twin.per_kwp(wdf)
    feats = ML.build_features(pk, wdf)
    bundle = ML.train_corrector(pk, wdf, force=force_ml)
    ml = ML.predict(bundle, feats, pk)

    installed = hierarchy.scope_capacity_mw(scope, scenario)
    demand = hierarchy.scope_demand_profile(scope, scenario)

    now_local = pd.Timestamp.now(tz="Africa/Tunis")
    fut_start = now_local.ceil(f"{STEP_MINUTES}min")
    # window must start strictly in the future: at an exact mark, move one step ahead
    if fut_start <= now_local:
        fut_start += pd.Timedelta(minutes=STEP_MINUTES)
    # pad the end by one step so short horizons still return forecast steps
    fut_end = now_local + pd.Timedelta(hours=hours) + pd.Timedelta(minutes=STEP_MINUTES)
    win = (wdf.index >= fut_start) & (wdf.index <= fut_end)

    frame = pd.DataFrame({
        "ghi": pk["ghi_raw"].clip(lower=0),
        "ghi_clear": pk["ghi_clear"],
        "cloud": wdf["cloud_cover"].clip(0, 100),
        "temp": wdf["temperature_2m"],
        "inject_phys_mw": (pk["pv_w_per_kwp"] / 1000 * installed * 0.64).round(3),
        "inject_ml_mw": (ml["pv_w_per_kwp_ml"] / 1000 * installed * 0.64).round(3),
        "inject_lo": (ml["pi_lo"] / 1000 * installed * 0.64).round(3),
        "inject_hi": (ml["pi_hi"] / 1000 * installed * 0.64).round(3),
    })
    frame.loc[frame["ghi_clear"] <= 0, ["inject_phys_mw", "inject_ml_mw",
                                   "inject_lo", "inject_hi"]] = 0.0

    # demand profile (repeat across the window, keyed on the hour of the step)
    demand_mw_arr = frame.index.hour.to_series().map(demand).values
    # seasonal factor: monthly seasonality of STEG consumption (AC peak summer,
    # mild profile in winter). Applied on top of the calibrated scope profile.
    season_factor = frame.index.month.map(DEMAND_SEASON_FACTOR).values
    # temperature sensitivity (AC/climate): +X% demand per °C above reference
    temp_dev = np.clip(frame["temp"].values - DEMAND_TEMP_REF_C, 0, None)
    temp_factor = 1.0 + DEMAND_TEMP_COEF * temp_dev
    # weekend effect: Sat/Sun carry less industrial & commercial load
    dow = frame.index.dayofweek.values
    weekend_factor = np.where(dow >= 5, DEMAND_WEEKEND_FACTOR, 1.0)
    frame["demand_mw"] = (demand_mw_arr * season_factor * temp_factor
                          * weekend_factor).round(3)
    frame["net_mw"] = (frame["demand_mw"] - frame["inject_ml_mw"]).round(3)

    fut = frame.loc[win]
    alerts = _merge_overlaps(detect_ramp_alerts(fut))
    _append_actual_records(fut, scope, scenario, hours)

    # energy on the forecast grid: sum(MW) * step-hours (15 min => /4)
    dt_h = (fut.index[1] - fut.index[0]).total_seconds() / 3600.0 if len(fut) > 1 \
        else STEP_MINUTES / 60.0

    # LIVE solar share: how much of the perimeter's demand the solar fleet covers.
    # Ratio of the two 15-min energy totals ON THE SAME FUTURE WINDOW —
    # this is the real penetration %, computed from the forecast, not a constant.
    solar_gwh = float(fut["inject_ml_mw"].sum() / 1000.0 * dt_h)
    demo_gwh = float(fut["demand_mw"].sum() / 1000.0 * dt_h)
    solar_share_pct = (solar_gwh / demo_gwh * 100.0) if demo_gwh > 0 else 0.0

    # headline numbers for the scope
    day = fut.loc[(fut.index.day == fut.index.max().day)]
    summary = {
        "scope": scope,
        "installed_mw": installed,
        "source": wmeta.get("source", "?"),
        "updated_at": pd.Timestamp.now(tz="Africa/Tunis").isoformat(),
        "horizon_hours": hours,
        "peak_injection_mw": float(fut["inject_ml_mw"].max()),
        "peak_time": str(fut["inject_ml_mw"].idxmax()),
        "today_peak_mw": float(day["inject_ml_mw"].max()) if len(day) and day["inject_ml_mw"].max() > 0 else 0.0,
        "energy_gwh": solar_gwh,
        "demand_gwh": demo_gwh,
        "solar_share_pct": solar_share_pct,
        "net_peak_remaining": float((fut["demand_mw"] - fut["inject_ml_mw"]).min()),
        "n_alerts": len(alerts),
        "model": {
            "trained_at": bundle.get("trained_at"),
            "cal_rmse": bundle.get("cal_rmse"),
            "n_train": bundle.get("n_train"),
            "n_cal": bundle.get("n_cal"),
            "pi_lo": bundle.get("pi_lo"),
            "pi_hi": bundle.get("pi_hi"),
            "confidence": CONFIDENCE_LEVEL,
        },
    }

    payload = {
        "summary": summary,
        "alerts": alerts,
        "series": {
            "time": [t.isoformat() for t in fut.index],
            **{c: fut[c].round(3).tolist() for c in fut.columns},
        },
        "meta": {"config": "STEG_BULLETIN_2026", "scenario": scenario},
    }
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return {"frame": frame, "future": fut, "alerts": alerts, "summary": summary,
            "bundle": bundle, "weather_meta": wmeta, "installed": installed}


def detect_ramp_alerts(hourly):
    """Ramp alert per spec: drop of X% over the next 60 min."""
    out = []
    inj = hourly["inject_ml_mw"]
    step_h = (inj.index[1] - inj.index[0]).total_seconds() / 3600.0 if len(inj) > 1 \
        else STEP_MINUTES / 60.0
    lookahead = max(1, round(RAMP_WINDOW_MINUTES / 60.0 / step_h))
    for i in range(len(inj) - lookahead):
        t = inj.index[i]
        nxt = inj.index[i + lookahead]
        v0, v1 = inj.iloc[i], inj.iloc[i + lookahead]
        if v0 <= 1.0:  # night hours carry no ramp risk
            continue
        # genuine daylight ramp: clear-sky GHI must still be material at t1,
        # otherwise this is the ordinary daily sunset decay, not an event.
        ghi_t1 = hourly["ghi_clear"].iloc[i + lookahead]
        if ghi_t1 < 250:
            continue
        delta = (v0 - v1) / v0
        if delta >= RAMP_RED_THRESHOLD:
            level, color = "RED", "rouge"
            desc = "chute prévisionnelle sévère (>= 20% / 60 min)"
        elif delta >= RAMP_YELLOW_THRESHOLD:
            level, color = "YELLOW", "jaune"
            desc = "chute prévisionnelle (>= 10% / 60 min)"
        else:
            continue
        out.append({
            "t0": t.isoformat(),
            "t1": nxt.isoformat(),
            "drop_pct": round(float(delta * 100), 1),
            "v0_mw": round(float(v0), 2),
            "v1_mw": round(float(v1), 2),
            "level": level, "color": color, "description": desc,
        })
    return _merge_overlaps(out)


def _merge_overlaps(alerts):
    """Collapse overlapping 60-min ramp alerts into single events so a rolling
    cloud bank is reported once, with the worst drop of the sequence."""
    merged = []
    for a in sorted(alerts, key=lambda x: x["t0"]):
        if merged:
            prev = merged[-1]
            prev_t1 = pd.Timestamp(prev["t1"])
            if pd.Timestamp(a["t0"]) <= prev_t1:
                new_t1 = max(prev_t1, pd.Timestamp(a["t1"]))
                prev["t1"] = new_t1.isoformat()
                if a["drop_pct"] > prev["drop_pct"]:
                    prev.update({"drop_pct": a["drop_pct"], "v1_mw": a["v1_mw"],
                                 "level": a["level"], "color": a["color"],
                                 "description": a["description"]})
                continue
        merged.append(a)
    return merged