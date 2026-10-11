"""
Phase 2 v2: do fires add predictive power beyond the seasonal ramp and weather?

Run from repo root:   python stubble_pm25_phase2_v2.py
Needs:                master_with_weather.csv (from merge_weather.py)
Outputs:              ablation_v2_results.csv + printed tables

Changes vs v1:
  - every rung includes the calendar baseline, so fire/weather effects are INCREMENTS
  - log1p fire counts (counts differ 10x across years)
  - small, physically motivated feature sets (avoid overfitting ~200 rows)
  - Ridge alpha chosen by leave-one-SEASON-out inner CV (not leave-one-day-out)
  - within-season, trend-removed correlation: the cleanest test of "do fires matter?"
"""
import sys
import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# ---------------- CONFIG ----------------
DATA_PATH = "master_with_weather.csv"
DATE_COL, FIRE_COL, PM_COL = "date", "fire_count", "avg_pm25"
LOG_TARGET = False
DIWALI = ["2022-10-24", "2023-11-12", "2024-10-31", "2025-10-20"]  # verify
DIWALI_WINDOW_DAYS = 2
ALPHAS = np.logspace(0, 4, 25)
# ----------------------------------------


def load():
    df = pd.read_csv(DATA_PATH, parse_dates=[DATE_COL])
    for c in (DATE_COL, FIRE_COL, PM_COL):
        if c not in df.columns:
            print(f"Missing column {c}. Available: {list(df.columns)}")
            sys.exit(1)
    df = df.sort_values(DATE_COL).reset_index(drop=True)
    df["year"] = df[DATE_COL].dt.year
    # Guard: a season with no fires means the FIRMS merge failed
    tot = df.groupby("year")[FIRE_COL].sum(min_count=1)
    if tot.isna().any() or (tot == 0).any():
        raise ValueError(f"No usable fire data for some seasons:\n{tot}")
    df[FIRE_COL] = df[FIRE_COL].fillna(0)   # NaN = zero-fire day
    return df


def build_features(df):
    df = df.copy()
    g = df.groupby("year")
    df["lf"] = np.log1p(df[FIRE_COL])
    df["lf_lag1"] = g["lf"].shift(1)
    df["lf_roll3"] = g["lf"].transform(lambda s: s.rolling(3, min_periods=3).mean())
    df["lf_roll7"] = g["lf"].transform(lambda s: s.rolling(7, min_periods=7).mean())

    df["day_of_season"] = (df[DATE_COL] - pd.to_datetime(df["year"].astype(str) + "-10-01")).dt.days
    diwali = pd.to_datetime(DIWALI)
    df["diwali_window"] = df[DATE_COL].apply(
        lambda d: int(any(abs((d - x).days) <= DIWALI_WINDOW_DAYS for x in diwali)))
    df["is_weekend"] = (df[DATE_COL].dt.dayofweek >= 5).astype(int)

    if "karnal_align_mean" in df.columns:
        df["karnal_align_lag1"] = g["karnal_align_mean"].shift(1)
        df["fire_x_align"] = df["lf_roll3"] * df["karnal_align_lag1"].clip(lower=0)
    if "delhi_blh_mean" in df.columns and "delhi_wind_speed_mean" in df.columns:
        df["ventilation"] = df["delhi_blh_mean"] * df["delhi_wind_speed_mean"]
    df["pm25_lag1"] = g[PM_COL].shift(1)
    return df


def feature_sets(df):
    calendar = ["day_of_season", "diwali_window", "is_weekend"]
    fires = ["lf", "lf_roll3", "lf_roll7"]
    weather = [c for c in ["delhi_wind_speed_mean", "delhi_temp_mean", "delhi_rh_mean",
                           "delhi_precip_sum", "ventilation", "karnal_align_lag1"]
               if c in df.columns]
    inter = [c for c in ["fire_x_align"] if c in df.columns]
    return {
        "A. calendar baseline": calendar,
        "B. calendar + fires": calendar + fires,
        "C. calendar + weather": calendar + weather,
        "D. calendar + fires + weather": calendar + fires + weather + inter,
        "E. calendar + yesterday PM2.5": calendar + ["pm25_lag1"],
        "F. everything + yesterday PM2.5": calendar + fires + weather + inter + ["pm25_lag1"],
    }


def to_t(y): return np.log(y) if LOG_TARGET else y
def from_t(y): return np.exp(y) if LOG_TARGET else y


def make_model(train_years):
    # Inner CV leaves out whole seasons, so alpha is chosen for cross-season generalization
    splits = [(np.where(train_years != y)[0], np.where(train_years == y)[0])
              for y in np.unique(train_years)]
    return make_pipeline(StandardScaler(), RidgeCV(alphas=ALPHAS, cv=splits))


def loso_eval(df, cols):
    rows = []
    for ty in sorted(df["year"].unique()):
        tr, te = df[df["year"] != ty], df[df["year"] == ty]
        m = make_model(tr["year"].values)
        m.fit(tr[cols], to_t(tr[PM_COL]))
        pred = from_t(m.predict(te[cols]))
        rows.append({"test_year": ty, "r2": r2_score(te[PM_COL], pred),
                     "mae": mean_absolute_error(te[PM_COL], pred)})
    return pd.DataFrame(rows)


def detrend(x, day):
    """Remove a linear trend in day-of-season; return residuals."""
    coef = np.polyfit(day, x, 1)
    return x - np.polyval(coef, day)


def within_season_test(df):
    """Correlate PM2.5 and fire activity AFTER removing each season's Oct-Nov ramp."""
    print("\n=== Within-season, trend-removed correlation (log PM2.5 vs fire activity) ===")
    print("Asks: on days with more fires than usual for that point in the season,")
    print("is Delhi smoggier than usual for that point in the season?\n")
    rows = []
    for yr, d in df.dropna(subset=["lf_roll3", PM_COL]).groupby("year"):
        pm_r = detrend(np.log(d[PM_COL].values), d["day_of_season"].values)
        out = {"season": yr, "n_days": len(d)}
        for col in ["lf", "lf_roll3", "lf_roll7"]:
            f_r = detrend(d[col].values, d["day_of_season"].values)
            out[f"r({col})"] = round(float(np.corrcoef(pm_r, f_r)[0, 1]), 3)
        rows.append(out)
    res = pd.DataFrame(rows)
    print(res.to_string(index=False))
    print("\nMean across seasons:", res.drop(columns=["season", "n_days"]).mean().round(3).to_dict())
    return res


def main():
    df = build_features(load())
    sets = feature_sets(df)
    cols_all = sorted({c for v in sets.values() for c in v})
    n0 = len(df)
    df = df.dropna(subset=cols_all + [PM_COL]).reset_index(drop=True)
    print(f"Rows: {n0} -> {len(df)} after dropping rows with NaN lags/weather")
    print("Rows per season:", df.groupby("year").size().to_dict(), "\n")

    results, summary = [], []
    for name, cols in sets.items():
        r = loso_eval(df, cols)
        r.insert(0, "model", name)
        results.append(r)
        row = {"model": name, "n_feat": len(cols), "mean_R2": round(r["r2"].mean(), 3),
               "mean_MAE": round(r["mae"].mean(), 1)}
        for _, x in r.iterrows():
            row[f"R2_{int(x['test_year'])}"] = round(x["r2"], 3)
        summary.append(row)
    pd.concat(results).to_csv("ablation_v2_results.csv", index=False)
    print("=== Leave-one-season-out results (R2 on the held-out season) ===")
    print(pd.DataFrame(summary).to_string(index=False))
    print("\nRead it as increments: B vs A = what fires add; C vs A = what weather adds;")
    print("D vs C = what fires add ON TOP of weather. E/F use yesterday's PM2.5 (forecast ceiling).")

    within_season_test(df)


if __name__ == "__main__":
    main()
