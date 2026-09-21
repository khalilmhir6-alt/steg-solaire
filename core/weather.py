"""
Weather ingestion: Open-Meteo archive+forecast, with a deterministic mock used
as fallback when offline (keeps the demo fully usable without internet).
"""

import json
import math
import random
from datetime import datetime, timedelta

import pandas as pd
import requests

from config import (
    LATITUDE,
    LONGITUDE,
    TIMEZONE,
    STEP_MINUTES,
    FORECAST_DAYS,
    WEATHER_VARIABLES,
    WEATHER_LIVE_PATH,
    WEATHER_MOCK_PATH,
    OPEN_METEO_URL,
)

# Past horizon in days; open-meteo requires ISO archive timezone fixed to UTC,
# while forecast comes back in the requested timezone.
ARCHIVE_DAYS = 60
# Forward coverage of the offline mock: the full week, matching the widest horizon.
FEED_FORWARD_HOURS = FORECAST_DAYS * 24


def moment_now():
    return datetime.now()


def _drifting_seed_localdate():
    # deterministic per 5-min bucket so consecutive refreshes differ slightly
    # (simulates a live feed) while staying stable within one bucket
    return (LATITUDE * 977 + LONGITUDE * 13
            + int(datetime.now().strftime("%Y%m%d%H%M")) // 5) % 1_000_000


def _mock_series(hours_future=None):
    """Synthetic weather resembling a sunny-to-convective Tunis day,
    with physically-sound GHI -> diffuse/DNI decomposition via real geometry."""
    import pvlib

    hours_future = hours_future or FEED_FORWARD_HOURS
    rng = random.Random(_drifting_seed_localdate())
    ref = datetime.now().replace(minute=0, second=0, microsecond=0)
    start = ref - timedelta(hours=ARCHIVE_DAYS * 24)
    idx = pd.date_range(start, periods=ARCHIVE_DAYS * 24 + hours_future + 1, freq="h", tz=TIMEZONE)

    solpos = pvlib.solarposition.get_solarposition(idx.tz_convert("UTC"), LATITUDE, LONGITUDE)
    cosz = solpos["apparent_zenith"].apply(lambda z: max(0.05, float(pvlib.tools.cosd(z))))

    rows = []
    for i, t in enumerate(idx):
        hour = t.hour
        day = t.timetuple().tm_yday
        base = max(0.0, 1 - abs(hour - 12.2) / 7.5)  # 0..1 daylight envelope
        drift = 0.9 + 0.1 * ((day * 7 + t.month) % 11) / 5
        ghi = 1100 * base * drift
        cloud_event = rng.random() < 0.12
        cloudfrac = rng.random() * 0.85 if cloud_event else rng.random() * 0.30
        ghi *= (1 - cloudfrac * 0.70)
        if base > 0:
            ghi = max(0.0, round(min(1150, ghi + (rng.random() - 0.5) * 20), 1))
        else:
            ghi = 0.0
        # diffuse fraction grows with cloud; DNI = (GHI - DHI)/cos(z), capped
        diffuse_frac = 0.18 + cloudfrac * 0.55 if base > 0 else 1.0
        dhi = round(max(0.0, ghi * diffuse_frac), 1)
        dni = round(max(0.0, min(1000.0, (ghi - dhi) / cosz.iloc[i])), 1)
        cloud = round(max(0.0, min(100.0, cloudfrac * 100.0)), 1)
        # realistic Tunis temperature: seasonal (cos peak ~21 July) + diurnal
        # (max ~14:30) around an annual mean of ~20 C. Keeps AC load (24C ref)
        # active in summer and dormant in winter.
        season = math.cos(2 * math.pi * (day - 205) / 365.0)
        mean_t = 20.0 + 8.0 * season
        diel = 7.0 * math.cos(2 * math.pi * (hour - 14.5) / 24.0)
        temp = round(mean_t + diel + (rng.random() - 0.5) * 2.5, 1)
        rh = round(max(30, min(90, 72 - 18 * base + (rng.random() - 0.5) * 8)), 1)
        ws = round(4 + 2.2 * (1 - base) + rng.random() * 2.5, 1)
        rows.append({
            "time": t,
            "shortwave_radiation": ghi,
            "direct_normal_irradiance": dni,
            "diffuse_radiation": dhi,
            "cloud_cover": cloud,
            "temperature_2m": temp,
            "relative_humidity_2m": rh,
            "wind_speed_10m": ws,
        })
    df = pd.DataFrame(rows).set_index("time")
    meta = {
        "source": "mock-synthetic-steg",
        "generated_at": moment_now().isoformat(),
        "lat": LATITUDE, "lon": LONGITUDE,
    }
    with open(WEATHER_MOCK_PATH, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "hours": [
            {"time": t.isoformat(), **{k: v for k, v in r.items() if k != "time"}}
            for t, r in df.iterrows()
        ]}, f, ensure_ascii=False)
    return df, meta


def _fetch_live():
    """Live Open-Meteo archive 60d + 7d forecast. Raises on failure."""
    now_utc = moment_now()
    past_start = (now_utc - timedelta(days=ARCHIVE_DAYS)).strftime("%Y-%m-%d")
    today = now_utc.strftime("%Y-%m-%d")

    responses = [
        # historical + current values (UTC)
        requests.get(OPEN_METEO_URL, params={
            "latitude": LATITUDE, "longitude": LONGITUDE,
            "start_date": past_start, "end_date": today,
            "hourly": ",".join(WEATHER_VARIABLES),
            "timezone": "UTC",
            "past_days": ARCHIVE_DAYS,
        }, timeout=(5, 10)),
        # forecast
        requests.get(OPEN_METEO_URL, params={
            "latitude": LATITUDE, "longitude": LONGITUDE,
            "hourly": ",".join(WEATHER_VARIABLES),
            "forecast_days": 7,
            "timezone": TIMEZONE,
        }, timeout=(5, 10)),
    ]
    for r in responses:
        r.raise_for_status()
    hist = responses[0].json()["hourly"]
    fut = responses[1].json()["hourly"]

    def blocks(data, tz):
        df = pd.DataFrame(data)
        df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(tz).dt.tz_convert(TIMEZONE)
        return df.set_index("time")

    df_hist = blocks(hist, "UTC")
    df_fut = blocks(fut, TIMEZONE)
    df = pd.concat([df_hist, df_fut]).apply(pd.to_numeric)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    meta = {"source": "open-meteo-live", "generated_at": moment_now().isoformat(),
            "lat": LATITUDE, "lon": LONGITUDE, "archive_days": ARCHIVE_DAYS}
    with open(WEATHER_LIVE_PATH, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "hours": [
            {"time": t.isoformat(), **{k: v for k, v in r.items()}}
            for t, r in df.iterrows()
        ]}, f, ensure_ascii=False)
    return df, meta


def _to_step(df, minutes=STEP_MINUTES):
    """Resample an hourly weather frame onto the configured forecast grid
    (default 15 min) via linear interpolation — smooth, physical GHI/DNI/etc."""
    if df is None or len(df) < 2:
        return df
    return (df.resample(f"{minutes}min")
              .interpolate(method="linear", limit_direction="both"))


def fetch(force_refresh=False, allow_mock=True):
    """Return (df on the 15-min grid in local TZ, meta). Live -> cache -> mock."""
    df = meta = None
    if not force_refresh:
        for path in (WEATHER_LIVE_PATH, WEATHER_MOCK_PATH):
            if _cache_fresh(path):
                df, meta = _read_cache(path)
                if df is not None:
                    break
    if df is None:
        try:
            df, meta = _fetch_live()
        except Exception:
            if not allow_mock:
                raise
            if not force_refresh and _cache_fresh(WEATHER_MOCK_PATH):
                df, meta = _read_cache(WEATHER_MOCK_PATH)
            if df is None:
                df, meta = _mock_series()
    return _to_step(df), meta


def _cache_fresh(path, max_age_minutes=90):
    import os
    return os.path.exists(path) and (moment_now() - datetime.fromtimestamp(
        os.path.getmtime(path))).total_seconds() < max_age_minutes * 60


def _read_cache(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        df = pd.DataFrame(payload["hours"])
        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time").sort_index()
        if df.index.tz is None:
            df.index = df.index.tz_localize(TIMEZONE)
        return df, payload.get("meta", {"source": "cache"})
    except Exception:
        return None, None