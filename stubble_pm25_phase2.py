"""
Phase 2 / Step 3: weather features + ablation ladder with leave-one-season-out CV.

Run from repo root (after merge_weather.py):   python stubble_pm25_phase2.py
Outputs: ablation_results.csv, prints a comparison table + standardized coefficients.

The key question answered: how much do FIRES add once WEATHER is accounted for?
  gap between 'weather+calendar (no fires)' and 'fires+weather+calendar'
"""
import sys
import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# ---------------- CONFIG: edit to match your master CSV ----------------
DATA_PATH = "master_with_weather.csv"
DATE_COL = "date"
FIRE_COL = "fire_count"     # daily fire detections over Punjab/Haryana
PM_COL = "avg_pm25"             # Delhi-NCR daily PM2.5
LOG_TARGET = False          # True = model log(PM2.5); False keeps it comparable to Phase 1

# Diwali dates (verify against an official calendar). Window = +/- 2 days.
DIWALI = ["2022-10-24", "2023-11-12", "2024-10-31", "2025-10-20"]
DIWALI_WINDOW_DAYS = 2
# -----------------------------------------------------------------------


def load():
    df = pd.read_csv(DATA_PATH)
    for c in (DATE_COL, FIRE_COL, PM_COL):
        if c not in df.columns:
            print(f"Column '{c}' not found. Available columns:\n{list(df.columns)}")
            print("Edit the CONFIG block at the top of this file.")
            sys.exit(1)
    df[DATE_COL] = pd.to_datetime(df[DATE_COL])
    return df.sort_values(DATE_COL).reset_index(drop=True)


def build_features(df):
    df = df.copy()
    df["year"] = df[DATE_COL].dt.year
    g = df.groupby("year")        # lags computed within each season, never across years

    # --- fire features ---
    for k in (1, 2, 3):
        df[f"fire_lag{k}"] = g[FIRE_COL].shift(k)
    df["fire_cum3"] = g[FIRE_COL].transform(lambda s: s.rolling(3, min_periods=3).sum())
    df["fire_cum7"] = g[FIRE_COL].transform(lambda s: s.rolling(7, min_periods=7).sum())

    # --- weather features (Delhi + upwind) ---
    if "delhi_align_mean" in df.columns:
        df["delhi_align_lag1"] = g["delhi_align_mean"].shift(1)
    if "karnal_align_mean" in df.columns:
        df["karnal_align_lag1"] = g["karnal_align_mean"].shift(1)
        # fires only matter if wind carries smoke toward Delhi
        df["fire_x_align"] = df["fire_cum3"] * df["karnal_align_lag1"].clip(lower=0)
    if "delhi_blh_mean" in df.columns:
        df["ventilation"] = df["delhi_blh_mean"] * df["delhi_wind_speed_mean"]

    # --- calendar / non-fire confounders ---
    diwali = pd.to_datetime(DIWALI)
    df["diwali_window"] = df[DATE_COL].apply(
        lambda d: int(any(abs((d - x).days) <= DIWALI_WINDOW_DAYS for x in diwali))
    )
    df["day_of_season"] = (df[DATE_COL] - pd.to_datetime(df["year"].astype(str) + "-10-01")).dt.days
    df["is_weekend"] = (df[DATE_COL].dt.dayofweek >= 5).astype(int)

    # --- persistence (separate rung: forecasting ceiling, not attribution) ---
    df["pm25_lag1"] = g[PM_COL].shift(1)
    return df


def feature_sets(df):
    fire = [FIRE_COL, "avg_frp", "max_frp", "fire_lag1", "fire_lag2", "fire_lag3", "fire_cum3", "fire_cum7"]
    weather_candidates = [
        "delhi_wind_speed_mean", "delhi_align_mean", "delhi_align_lag1",
        "karnal_align_mean", "karnal_align_lag1",
        "delhi_temp_mean", "delhi_temp_min", "delhi_rh_mean", "delhi_precip_sum",
        "delhi_blh_mean", "ventilation",
    ]
    weather = [c for c in weather_candidates if c in df.columns]
    interaction = [c for c in ["fire_x_align"] if c in df.columns]
    calendar = ["diwali_window", "day_of_season", "is_weekend"]

    return {
        "1. calendar only": calendar,
        "2. weather + calendar (no fires)": weather + calendar,
        "3. fires only (Phase 1 style)": fire,
        "4. fires + weather + calendar": fire + weather + interaction + calendar,
        "5. + yesterday's PM2.5 (forecast ceiling)": fire + weather + interaction + calendar + ["pm25_lag1"],
    }


def to_target(y):
    return np.log(y) if LOG_TARGET else y


def from_target(y):
    return np.exp(y) if LOG_TARGET else y


def loso_eval(df, cols):
    """Leave-one-season-out: train on 3 seasons, test on the 4th."""
    rows = []
    for test_year in sorted(df["year"].unique()):
        tr, te = df[df["year"] != test_year], df[df["year"] == test_year]
        model = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 25)))
        model.fit(tr[cols], to_target(tr[PM_COL]))
        pred = from_target(model.predict(te[cols]))
        rows.append({
            "test_year": test_year,
            "r2": r2_score(te[PM_COL], pred),
            "mae": mean_absolute_error(te[PM_COL], pred),
            "n": len(te),
        })
    return pd.DataFrame(rows)


def main():
    df = build_features(load())
    sets = feature_sets(df)

    # Same rows for every model so the comparison is fair
    all_cols = sorted({c for cols in sets.values() for c in cols})
    df = df.dropna(subset=all_cols + [PM_COL]).reset_index(drop=True)
    print(f"Rows used (identical for every model): {len(df)}  | seasons: {sorted(df['year'].unique())}\n")

    results, summary = [], []
    for name, cols in sets.items():
        res = loso_eval(df, cols)
        res.insert(0, "model", name)
        results.append(res)
        r2_2025 = res.loc[res["test_year"] == 2025, "r2"]
        summary.append({
            "model": name,
            "n_features": len(cols),
            "mean_R2 (4 folds)": round(res["r2"].mean(), 3),
            "R2 on 2025": round(float(r2_2025.iloc[0]), 3) if len(r2_2025) else np.nan,
            "mean_MAE": round(res["mae"].mean(), 1),
        })

    pd.concat(results).to_csv("ablation_results.csv", index=False)
    print(pd.DataFrame(summary).to_string(index=False))

    # Standardized coefficients for the full model (fit on all seasons)
    cols = sets["4. fires + weather + calendar"]
    model = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 25)))
    model.fit(df[cols], to_target(df[PM_COL]))
    coefs = pd.Series(model[-1].coef_, index=cols).sort_values(key=abs, ascending=False)
    print("\nStandardized coefficients (full model; larger |value| = stronger effect):")
    print(coefs.round(3).to_string())
    print("\nSaved ablation_results.csv")


if __name__ == "__main__":
    main()
