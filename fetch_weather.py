"""
Phase 2 / Step 1: fetch daily weather for Delhi + upwind points from Open-Meteo.

Run from repo root:   python fetch_weather.py
Output:               weather_daily.csv  (one row per date, prefixed columns per location)

No API key needed. Winds are requested in m/s. Times are Asia/Kolkata (IST).
"""
import time
import numpy as np
import pandas as pd
import requests

# ---------------- CONFIG ----------------
YEARS = [2022, 2023, 2024, 2025]
SEASON_START = "09-24"   # a week+ before Oct 1 so lag/rolling features have history
SEASON_END = "11-30"

POINTS = {
    "delhi": (28.61, 77.21),
    "karnal": (29.69, 76.99),     # upwind, Haryana
    "ludhiana": (30.90, 75.85),   # upwind, Punjab
}
SOURCE = (30.3, 75.8)             # rough centre of the burning region (Punjab)
DEST = (28.61, 77.21)             # Delhi
OUT_PATH = "weather_daily.csv"
# ----------------------------------------

URL = "https://archive-api.open-meteo.com/v1/archive"
BASE_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "precipitation",
]
OPTIONAL_VARS = ["boundary_layer_height"]  # not always available in the archive API


def bearing_unit_vector(src, dst):
    """Unit vector (east, north) pointing from src toward dst."""
    lat1, lon1 = np.radians(src)
    lat2, lon2 = np.radians(dst)
    dlon = lon2 - lon1
    x = np.sin(dlon) * np.cos(lat2)
    y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dlon)
    b = np.arctan2(x, y)
    return np.sin(b), np.cos(b)


E_VEC, N_VEC = bearing_unit_vector(SOURCE, DEST)


def request_hourly(lat, lon, start, end, variables, retries=3):
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "hourly": ",".join(variables),
        "wind_speed_unit": "ms",
        "timezone": "Asia/Kolkata",
    }
    for attempt in range(retries):
        r = requests.get(URL, params=params, timeout=60)
        if r.status_code == 429:           # rate limited
            time.sleep(10 * (attempt + 1))
            continue
        return r
    return r


def fetch_point(lat, lon, start, end, use_optional):
    variables = BASE_VARS + (OPTIONAL_VARS if use_optional else [])
    r = request_hourly(lat, lon, start, end, variables)
    if r.status_code == 400 and use_optional:
        print("  (boundary_layer_height not available here; retrying without it)")
        return fetch_point(lat, lon, start, end, use_optional=False), False
    r.raise_for_status()
    df = pd.DataFrame(r.json()["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    return df, use_optional


def to_daily(hourly, prefix):
    h = hourly.copy()
    wd = np.radians(h["wind_direction_10m"])          # direction wind blows FROM
    h["u"] = -h["wind_speed_10m"] * np.sin(wd)        # east component (blowing toward)
    h["v"] = -h["wind_speed_10m"] * np.cos(wd)        # north component
    # Positive = wind carrying air from the burning region toward Delhi
    h["align"] = h["u"] * E_VEC + h["v"] * N_VEC
    h["date"] = h["time"].dt.normalize()

    agg = {
        "wind_speed_mean": ("wind_speed_10m", "mean"),
        "u_mean": ("u", "mean"),
        "v_mean": ("v", "mean"),
        "align_mean": ("align", "mean"),
        "align_max": ("align", "max"),
        "temp_mean": ("temperature_2m", "mean"),
        "temp_min": ("temperature_2m", "min"),
        "rh_mean": ("relative_humidity_2m", "mean"),
        "precip_sum": ("precipitation", "sum"),
    }
    if "boundary_layer_height" in h.columns:
        agg["blh_mean"] = ("boundary_layer_height", "mean")
        agg["blh_min"] = ("boundary_layer_height", "min")

    daily = h.groupby("date").agg(**agg)
    daily.columns = [f"{prefix}_{c}" for c in daily.columns]
    return daily


def main():
    use_optional = True
    frames = []
    for name, (lat, lon) in POINTS.items():
        print(f"Fetching {name} ({lat}, {lon})")
        parts = []
        for yr in YEARS:
            hourly, use_optional = fetch_point(
                lat, lon, f"{yr}-{SEASON_START}", f"{yr}-{SEASON_END}", use_optional
            )
            parts.append(to_daily(hourly, name))
            time.sleep(1)  # be polite to the free API
        frames.append(pd.concat(parts))

    out = pd.concat(frames, axis=1).reset_index()
    out.to_csv(OUT_PATH, index=False)
    print(f"\nSaved {OUT_PATH}: {out.shape[0]} days x {out.shape[1]} columns")
    print("Boundary layer height included:", any("blh" in c for c in out.columns))


if __name__ == "__main__":
    main()
