import pandas as pd, glob, os
folder = r"F:\Stubble Burning\AQI Datasets"
for f in sorted(glob.glob(os.path.join(folder, "*.csv"))):
    df = pd.read_csv(f)
    print(os.path.basename(f), "| rows:", len(df))
    if "acq_date" in df:
        print("   dates:", df["acq_date"].min(), "->", df["acq_date"].max())
    if "satellite" in df:
        print("   satellite:", df["satellite"].value_counts().to_dict())