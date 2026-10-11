"""
Phase 2 / Step 2: merge weather_daily.csv into your Phase 1 master table.

Run from repo root (after fetch_weather.py):   python merge_weather.py
Output:  master_with_weather.csv
"""
import sys
import pandas as pd

# ---------------- CONFIG ----------------
MASTER_PATH = "master_dashboard_data.csv"   # produced by prepare_dashboard_data.py
WEATHER_PATH = "weather_daily.csv"
OUT_PATH = "master_with_weather.csv"
DATE_COL = "date"                           # date column name in your master CSV
# ----------------------------------------


def main():
    master = pd.read_csv(MASTER_PATH)
    if DATE_COL not in master.columns:
        print(f"Column '{DATE_COL}' not found in {MASTER_PATH}.")
        print("Columns are:", list(master.columns))
        sys.exit(1)

    weather = pd.read_csv(WEATHER_PATH)
    master[DATE_COL] = pd.to_datetime(master[DATE_COL]).dt.normalize()
    weather["date"] = pd.to_datetime(weather["date"]).dt.normalize()

    merged = master.merge(weather, left_on=DATE_COL, right_on="date",
                          how="left", suffixes=("", "_w"))
    if DATE_COL != "date":
        merged = merged.drop(columns=["date"])

    wcols = [c for c in weather.columns if c != "date"]
    missing = merged[wcols[0]].isna().sum()
    print(f"Master rows: {len(master)} | merged rows: {len(merged)}")
    print(f"Rows with no weather match: {missing}")
    if missing:
        print(merged.loc[merged[wcols[0]].isna(), DATE_COL].dt.date.tolist())

    merged.to_csv(OUT_PATH, index=False)
    print(f"Saved {OUT_PATH}")
    print("Master columns:", list(master.columns))


if __name__ == "__main__":
    main()
