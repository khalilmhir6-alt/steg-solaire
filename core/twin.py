"""
Digital twin: physical geometry (pvlib) converting weather into per-kWp
production and per-MW AC injection for a given site/scenario.

Scoping philosophy (STEG):
  - geometry is computed ONCE on the Tunis templates,
  - per-MW AC injection then scales linearly with installed capacity,
      exactly as STEG stats do (injection [GWh] / MWp installed).
"""

from datetime import datetime

import pandas as pd
import pvlib

from config import (
    LATITUDE,
    LONGITUDE,
    TILT_ANGLE,
    AZIMUTH,
    DERATE_FACTOR,
    ALBEDO,
    SURFACE_TYPE,
)

SITE = pvlib.location.Location(LATITUDE, LONGITUDE)


def _solpos(idx_local):
    return pvlib.solarposition.get_solarposition(
        idx_local.tz_convert("UTC"), LATITUDE, LONGITUDE
    )


def _airmass_absolute(solpos):
    rel = pvlib.atmosphere.get_relative_airmass(solpos["zenith"])
    return pvlib.atmosphere.get_absolute_airmass(rel)


def clear_sky_series(start, periods_hours):
    """Clear-sky per-kWp series (W/kWp) for the given pinned local window."""
    times = pd.date_range(start, periods=periods_hours, freq="h")
    if times.tz is None:
        times = times.tz_localize("Africa/Tunis")
    solpos = _solpos(times)
    clearsky = pvlib.clearsky.ineichen(
        solpos["apparent_zenith"], _airmass_absolute(solpos),
        linke_turbidity=3.0,
    )
    clearsky = clearsky.dropna()
    clearsky = clearsky[~clearsky.index.duplicated(keep="first")]
    return clearsky.tz_convert("Africa/Tunis")


def per_kwp(df_weather):
    """Map hourly weather frame -> DataFrame(ghi_raw, ghi_clear, poa, pv_w_per_kwp)."""
    idx = df_weather.index
    solpos = _solpos(idx)
    airmass_abs = _airmass_absolute(solpos)
    cs = pvlib.clearsky.ineichen(
        solpos["apparent_zenith"], airmass_abs, linke_turbidity=3.0,
    )
    ghi_clear = cs["ghi"].clip(lower=0)
    ghi_raw = df_weather["shortwave_radiation"].clip(lower=0)

    poa = pvlib.irradiance.get_total_irradiance(
        TILT_ANGLE, AZIMUTH,
        solar_zenith=solpos["apparent_zenith"],
        solar_azimuth=solpos["azimuth"],
        dni=df_weather["direct_normal_irradiance"].clip(lower=0),
        ghi=ghi_raw,
        dhi=df_weather["diffuse_radiation"].clip(lower=0),
        dni_extra=pvlib.irradiance.get_extra_radiation(idx.tz_convert("UTC")),
        albedo=ALBEDO,
        surface_type=SURFACE_TYPE,
        model="haydavies",
    )["poa_global"].clip(lower=0)

    dc = pvlib.pvsystem.pvwatts_dc(
        poa, 25.0, pdc0=1000.0, gamma_pdc=-0.0025  # nominal 1 kWp, T=25
    )
    out = pd.DataFrame({
        "ghi_raw": ghi_raw,
        "ghi_clear": ghi_clear,
        "poa": poa,
        "pv_w_per_kwp": (dc * DERATE_FACTOR).round(3),
    })
    out.index = idx
    return out


def injectable_mw(per_kwp_df, installed_mw, injection_ratio=0.64):
    """
    Raw AC injection profile = per-kWp capacity factor * installed MW (MW).

    STEG observes that only ~64% of generated PV energy is ever injected
    (bulletin: 2358 GWh produced vs 1511 GWh injected since 2011). The rest
    is self-consumed on-site or curtailed on peak (over-injection). We apply
    that ratio at fleet level for a realistic injected-power curve.
    """
    mw = per_kwp_df["pv_w_per_kwp"] / 1000.0 * installed_mw * injection_ratio
    return mw.clip(lower=0.0).round(3)


def hour_now_local():
    return datetime.now().astimezone().replace(tzinfo=None).replace(microsecond=0)