"""
Stubble Burning & Delhi-NCR Air Quality Dashboard
Data prep script: merges NASA FIRMS fire data + OpenAQ air quality data
into one clean daily master table, ready to load into Power BI.

BEFORE RUNNING:
1. pip install pandas requests
2. Put all your FIRMS CSVs in a folder called "firms_data/" next to this script
   (2022, 2023 will have both NOAA-20 and S-NPP rows mixed in -- that's fine,
   this script filters to NOAA-20 only automatically)
3. Fill in your OpenAQ API key below
"""

import pandas as pd
import requests
import glob
import time
import os

OPENAQ_API_KEY = os.environ.get("OPENAQ_API_KEY")
if not OPENAQ_API_KEY:
    raise EnvironmentError(
        "OPENAQ_API_KEY not found. Set it as an environment variable before running:\n"
        "  Windows (PowerShell):  $env:OPENAQ_API_KEY = \"your-key-here\"\n"
        "  Windows (cmd):         set OPENAQ_API_KEY=your-key-here\n"
        "  Mac/Linux:             export OPENAQ_API_KEY=\"your-key-here\"\n"
        "Then run the script again in the SAME terminal window."
    )

# =========================================================
# STEP 1: Load and merge all FIRMS fire CSVs
# =========================================================

FIRMS_FOLDER = r"F:\Stubble Burning\AQI Datasets"  # <-- update to your actual FIRMS folder

def load_firms_data(folder):
    patterns = ["fire_archive_J1V*.csv", "fire_nrt_J1V*.csv"]
    all_files = []
    for p in patterns:
        all_files += glob.glob(os.path.join(folder, p))
    if not all_files:
        raise FileNotFoundError(f"No J1V CSVs found in '{folder}'.")

    dfs = []
    for f in all_files:
        df = pd.read_csv(f)
        dfs.append(df)
        print(f"Loaded {os.path.basename(f)}: {len(df)} rows")

    fire_df = pd.concat(dfs, ignore_index=True)
    fire_df["acq_date"] = pd.to_datetime(fire_df["acq_date"])

    # Archive + NRT files can overlap; don't double count
    before = len(fire_df)
    fire_df = fire_df.drop_duplicates(subset=["latitude", "longitude", "acq_date", "acq_time"])
    print(f"Dropped {before - len(fire_df)} duplicate detections")

    # Safety check: every season must have fire data
    per_year = fire_df.groupby(fire_df["acq_date"].dt.year).size()
    print("\nFire detections per year:\n", per_year)
    for yr in (2022, 2023, 2024, 2025):
        if per_year.get(yr, 0) == 0:
            raise ValueError(f"No fire detections found for {yr}. Check your FIRMS files.")

    daily_fire = (
        fire_df.groupby("acq_date")
        .agg(fire_count=("latitude", "count"),
             avg_frp=("frp", "mean"),
             max_frp=("frp", "max"))
        .reset_index()
        .rename(columns={"acq_date": "date"})
    )
    return daily_fire


# =========================================================
# STEP 2: Pull daily PM2.5 data from OpenAQ for Delhi
# =========================================================

BASE_URL = "https://api.openaq.org/v3"
HEADERS = {"X-API-Key": OPENAQ_API_KEY}

# Rough bounding box around Delhi-NCR (west, south, east, north)
DELHI_BBOX = "76.8,28.4,77.5,28.9"

DATE_RANGES = [
    ("2022-10-01T00:00:00Z", "2022-11-30T23:59:59Z"),
    ("2023-10-01T00:00:00Z", "2023-11-30T23:59:59Z"),
    ("2024-10-01T00:00:00Z", "2024-11-30T23:59:59Z"),
    ("2025-10-01T00:00:00Z", "2025-11-30T23:59:59Z"),
]


def get_delhi_pm25_sensors():
    """Find all PM2.5 sensors in Delhi via the locations endpoint."""
    url = f"{BASE_URL}/locations"
    params = {"bbox": DELHI_BBOX, "parameters_id": 2, "limit": 100}  # 2 = PM2.5
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    locations = resp.json()["results"]

    sensor_ids = []
    for loc in locations:
        for sensor in loc.get("sensors", []):
            if sensor["parameter"]["name"] == "pm25":
                sensor_ids.append(sensor["id"])

    print(f"Found {len(sensor_ids)} PM2.5 sensors in Delhi")
    return sensor_ids


def get_daily_pm25(sensor_id, date_from, date_to, debug=False):
    """Pull daily-aggregated PM2.5 for one sensor over a date range."""
    url = f"{BASE_URL}/sensors/{sensor_id}/days"
    params = {
        "date_from": date_from,
        "date_to": date_to,
        "limit": 1000,
    }
    resp = requests.get(url, headers=HEADERS, params=params)

    if debug:
        print(f"\n--- DEBUG: full request URL ---")
        print(resp.url)
        print(f"--- DEBUG: status code: {resp.status_code} ---")
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            print(f"--- DEBUG: {len(results)} results returned ---")
            if results:
                first_date = results[0]["period"]["datetimeFrom"]["local"][:10]
                last_date = results[-1]["period"]["datetimeFrom"]["local"][:10]
                print(f"--- DEBUG: date range in response: {first_date} to {last_date} ---\n")
        else:
            print(f"--- DEBUG: response body: {resp.text[:500]} ---\n")

    if resp.status_code != 200:
        print(f"  Skipping sensor {sensor_id}: {resp.status_code}")
        return pd.DataFrame()

    results = resp.json().get("results", [])
    rows = []
    for r in results:
        rows.append({
            "date": r["period"]["datetimeFrom"]["local"][:10],
            "pm25": r["value"],
        })
    return pd.DataFrame(rows)


def load_openaq_data():
    sensor_ids = get_delhi_pm25_sensors()
    all_data = []

    for date_from, date_to in DATE_RANGES:
        print(f"\nPulling PM2.5 for {date_from} to {date_to}...")
        for i, sid in enumerate(sensor_ids):
            df = get_daily_pm25(sid, date_from, date_to, debug=(i == 0))
            if not df.empty:
                all_data.append(df)
            time.sleep(0.2)  # be polite to the API

    pm25_df = pd.concat(all_data, ignore_index=True)
    pm25_df["date"] = pd.to_datetime(pm25_df["date"])

    # Average across all Delhi stations per day
    daily_aqi = pm25_df.groupby("date")["pm25"].mean().reset_index()
    daily_aqi = daily_aqi.rename(columns={"pm25": "avg_pm25"})

    return daily_aqi


# =========================================================
# STEP 3: Merge fire + AQI into one master table
# =========================================================

def main():
    print("=== Loading FIRMS fire data ===")
    daily_fire = load_firms_data(FIRMS_FOLDER)

    print("\n=== Loading OpenAQ PM2.5 data ===")
    daily_aqi = load_openaq_data()

    print("\n=== Merging into master table ===")
    master = pd.merge(daily_fire, daily_aqi, on="date", how="outer").sort_values("date")

    # Flag missing AQI days rather than silently dropping them
    master["aqi_missing"] = master["avg_pm25"].isna()

    master.to_csv("master_dashboard_data.csv", index=False)
    print(f"\nDone. {len(master)} rows written to master_dashboard_data.csv")
    print(master.head(10))


if __name__ == "__main__":
    main()