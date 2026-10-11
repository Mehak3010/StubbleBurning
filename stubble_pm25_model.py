"""
Stubble Burning -> Delhi-NCR PM2.5 Model
==========================================
Phase 1 of the Stubble Burning project.

Predicts daily average Delhi-NCR PM2.5 from Punjab/Haryana crop-fire
activity (NASA FIRMS VIIRS, NOAA-20/J1V) using lagged and rolling fire
features. Data covers Oct-Nov across four seasons: 2022, 2023, 2024, 2025.

INPUTS
------
- master_dashboard_data.csv : daily fire_count / avg_frp / max_frp / avg_pm25,
  already merged from FIRMS + OpenAQ (see prepare_dashboard_data.py).

KNOWN DATA ISSUES (historical, already corrected in master_dashboard_data.csv)
-------------------------------------------------------------------------------
- The original raw fire_archive_J1V-C2_785706.csv (2024) was truncated to
  ~half its expected row count; corrected using cross-validated counts.
- 2025 fire counts (2,942 total, Oct-Nov) are genuinely far lower than prior
  seasons -- this is real, not a data error. Punjab reported an independently
  documented ~54% drop in stubble fires in 2025 vs. 2024 (PPCB data), part of
  a multi-year decline driven by CRM machinery subsidies and enforcement.

USAGE
-----
    python stubble_pm25_model.py
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import xgboost as xgb

MASTER_CSV = "master_dashboard_data.csv"  # from prepare_dashboard_data.py


def load_and_clean(path=MASTER_CSV):
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Guard: a season with mostly-missing or all-zero fires means the FIRMS merge failed
    yr = df["date"].dt.year
    cov = df.groupby(yr)["fire_count"].apply(lambda s: s.notna().mean())
    tot = df.groupby(yr)["fire_count"].sum()
    bad = sorted(set(cov[cov < 0.5].index) | set(tot[tot == 0].index))
    if bad:
        raise ValueError(f"No usable fire data for seasons {bad}; "
                         "fix the FIRMS merge before modeling.")

    for c in ["fire_count", "avg_frp", "max_frp"]:
        df[c] = df[c].fillna(0)                         # NaN = zero-fire day

    df["season"] = df["date"].dt.year
    df["day_of_season"] = df.groupby("season")["date"].transform(
        lambda s: (s - s.min()).dt.days
    )
    return df

def cross_correlation(df, max_lag=7):
    """Same-day vs lagged correlation between fire_count and avg_pm25."""
    rows = []
    for k in range(max_lag + 1):
        shifted = df.groupby("season")["fire_count"].shift(k)
        valid = shifted.notna()
        corr = np.corrcoef(shifted[valid], df.loc[valid, "avg_pm25"])[0, 1]
        rows.append({"lag_days": k, "correlation": round(corr, 4)})
    return pd.DataFrame(rows)


def engineer_features(df):
    g = df.groupby("season")
    for lag in [1, 2, 3]:
        df[f"fire_count_lag{lag}"] = g["fire_count"].shift(lag)
        df[f"avg_frp_lag{lag}"] = g["avg_frp"].shift(lag)
    df["fire_count_roll3"] = g["fire_count"].transform(lambda s: s.rolling(3, min_periods=1).sum())
    df["fire_count_roll7"] = g["fire_count"].transform(lambda s: s.rolling(7, min_periods=1).sum())
    df["max_frp_roll3"] = g["max_frp"].transform(lambda s: s.rolling(3, min_periods=1).max())
    return df.dropna().reset_index(drop=True)


FEATURES = [
    "fire_count", "avg_frp", "max_frp", "day_of_season",
    "fire_count_lag1", "fire_count_lag2", "fire_count_lag3",
    "avg_frp_lag1", "fire_count_roll3", "fire_count_roll7", "max_frp_roll3",
]
TARGET = "avg_pm25"


def train_and_evaluate(df_model):
    """Time-based split: train on 2022-2024, test on the held-out 2025 season
    (a genuinely future, out-of-sample year rather than an interpolated one)."""
    train = df_model[df_model["season"].isin([2022, 2023, 2024])]
    test = df_model[df_model["season"] == 2025]
    Xtr, ytr = train[FEATURES], train[TARGET]
    Xte, yte = test[FEATURES], test[TARGET]

    models = {
        "Ridge": Ridge(alpha=1.0),
        "RandomForest": RandomForestRegressor(n_estimators=400, max_depth=5, min_samples_leaf=3, random_state=42),
        "XGBoost": xgb.XGBRegressor(n_estimators=300, max_depth=3, learning_rate=0.05,
                                     subsample=0.8, colsample_bytree=0.8, random_state=42),
    }

    results, preds = {}, {"date": test["date"].values, "actual": yte.values}
    for name, model in models.items():
        model.fit(Xtr, ytr)
        pred = model.predict(Xte)
        preds[name] = pred
        results[name] = {
            "R2": r2_score(yte, pred),
            "MAE": mean_absolute_error(yte, pred),
            "RMSE": mean_squared_error(yte, pred) ** 0.5,
        }
    return results, pd.DataFrame(preds), models


if __name__ == "__main__":
    df = load_and_clean()
    print("Cross-correlation (fire activity leads PM2.5 by k days):")
    print(cross_correlation(df).to_string(index=False))

    df_model = engineer_features(df)
    results, preds_df, models = train_and_evaluate(df_model)

    print("\nModel performance on held-out 2025 season:")
    print(pd.DataFrame(results).T.round(3))

    # Refit Ridge on STANDARDIZED features so coefficients are comparable
    # across features with different scales (fire_count ~0-150 vs avg_frp ~2-10).
    # The unscaled model above is used for prediction/evaluation; this refit
    # is only for interpreting relative feature importance.
    train = df_model[df_model["season"].isin([2022, 2023, 2024])]
    scaler = StandardScaler().fit(train[FEATURES])
    Xtr_scaled = scaler.transform(train[FEATURES])
    ridge_scaled = Ridge(alpha=1.0).fit(Xtr_scaled, train[TARGET])
    importances = pd.Series(ridge_scaled.coef_, index=FEATURES)
    print("\nRidge coefficients (standardized scale, for interpretability only):")
    print(importances.sort_values(key=abs, ascending=False))