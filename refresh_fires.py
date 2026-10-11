import pandas as pd, glob, os, shutil

FOLDER = r"F:\Stubble Burning\AQI Datasets"
files = sorted(glob.glob(os.path.join(FOLDER, "fire_archive_J1V*.csv")))

dfs = []
for f in files:
    d = pd.read_csv(f)
    print(f"{os.path.basename(f)}: {len(d)} rows | {d['acq_date'].min()} -> {d['acq_date'].max()}")
    dfs.append(d)

fire = pd.concat(dfs, ignore_index=True)
fire["acq_date"] = pd.to_datetime(fire["acq_date"])
before = len(fire)
fire = fire.drop_duplicates(subset=["latitude", "longitude", "acq_date", "acq_time"])
print(f"\nDropped {before - len(fire)} duplicate detections")

per_year = fire.groupby(fire["acq_date"].dt.year).size()
print("\nDetections per year (all dates in files):\n", per_year)

daily = (fire.groupby("acq_date")
         .agg(fire_count=("latitude", "count"), avg_frp=("frp", "mean"), max_frp=("frp", "max"))
         .reset_index().rename(columns={"acq_date": "date"}))

shutil.copy("master_dashboard_data.csv", "master_dashboard_data_OLD.csv")  # backup
old = pd.read_csv("master_dashboard_data.csv", parse_dates=["date"])[["date", "avg_pm25", "aqi_missing"]]
master = old.merge(daily, on="date", how="left").sort_values("date")

cov = master.groupby(master["date"].dt.year)["fire_count"].apply(lambda s: s.notna().sum())
print("\nDays with fire data per season (should be ~61 or a bit fewer):\n", cov)
print("\nOct-Nov detections per season:\n", master.groupby(master["date"].dt.year)["fire_count"].sum())

master["fire_count"] = master["fire_count"].fillna(0)   # zero-fire days
master = master[["date", "fire_count", "avg_frp", "max_frp", "avg_pm25", "aqi_missing"]]
season_tot = master.groupby(master["date"].dt.year)["fire_count"].sum()
if (season_tot == 0).any():
    raise ValueError(f"A season has zero fires after merge:\n{season_tot}\nCheck the FIRMS files.")
master.to_csv("master_dashboard_data.csv", index=False)
print("\nSaved master_dashboard_data.csv")