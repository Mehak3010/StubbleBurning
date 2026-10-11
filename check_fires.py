import pandas as pd, glob
d = pd.read_csv("master_dashboard_data.csv")
d["date"] = pd.to_datetime(d["date"])
print(d[d["date"].dt.year == 2025][["date", "fire_count", "avg_pm25"]].head(5))
print("\nFire/FIRMS-looking files in this folder tree:")
for f in glob.glob("**/*.csv", recursive=True):
    print(" ", f)