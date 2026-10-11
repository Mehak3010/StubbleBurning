import pandas as pd
d = pd.read_csv("master_with_weather.csv")
d["year"] = pd.to_datetime(d["date"]).dt.year
print("Rows per year:\n", d.groupby("year").size(), "\n")
print("aqi_missing per year:\n", d.groupby("year")["aqi_missing"].sum(), "\n")
print("NaN counts by year (only columns with NaN):")
nan = d.drop(columns="year").isna().groupby(d["year"]).sum()
print(nan.loc[:, nan.sum() > 0])