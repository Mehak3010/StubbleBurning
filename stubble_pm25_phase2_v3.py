"""
Phase 2 v3: within-season anomaly analysis.

Run from repo root (same folder as stubble_pm25_phase2_v2.py):
    python stubble_pm25_phase2_v3.py

Idea: remove each season's quadratic Oct-Nov trend from log PM2.5, fire activity and
weather, then ask whether fire anomalies predict PM2.5 anomalies in a held-out season,
with and without weather. A 7-day block bootstrap gives an autocorrelation-aware CI.
"""
import numpy as np
import pandas as pd
from sklearn.metrics import r2_score

from stubble_pm25_phase2_v2 import (
    load, build_features, feature_sets, make_model, PM_COL, DATE_COL, FIRE_COL
)

CALENDAR = ["day_of_season", "diwali_window", "is_weekend"]
DEG = 2          # trend polynomial degree removed within each season
BLOCK = 7        # days per bootstrap block
N_BOOT = 2000


def season_anomalies(df, cols, deg=DEG):
    out = pd.DataFrame(index=df.index, columns=cols, dtype=float)
    for yr, idx in df.groupby("year").groups.items():
        x = df.loc[idx, "day_of_season"].values.astype(float)
        for c in cols:
            y = df.loc[idx, c].values.astype(float)
            out.loc[idx, c] = y - np.polyval(np.polyfit(x, y, deg), x)
    return out


def block_bootstrap_corr(df_anom, xcol, ycol, years, seed=0):
    rng = np.random.default_rng(seed)
    blocks = []
    for yr in np.unique(years):
        m = years == yr
        x, y = df_anom.loc[m, xcol].values, df_anom.loc[m, ycol].values
        for s in range(0, len(x), BLOCK):
            blocks.append((x[s:s + BLOCK], y[s:s + BLOCK]))
    stats = []
    for _ in range(N_BOOT):
        pick = rng.integers(0, len(blocks), len(blocks))
        xs = np.concatenate([blocks[i][0] for i in pick])
        ys = np.concatenate([blocks[i][1] for i in pick])
        stats.append(np.corrcoef(xs, ys)[0, 1])
    return np.percentile(stats, [2.5, 50, 97.5])


def loso_anomaly(anom, years, cols, target="log_pm"):
    rows = []
    for ty in sorted(np.unique(years)):
        tr, te = years != ty, years == ty
        m = make_model(years[tr])
        m.fit(anom.loc[tr, cols], anom.loc[tr, target])
        pred = m.predict(anom.loc[te, cols])
        rows.append(r2_score(anom.loc[te, target], pred))
    return rows


def main():
    df = build_features(load())
    sets = feature_sets(df)
    weather = [c for c in sets["C. calendar + weather"] if c not in CALENDAR]
    fires = ["lf", "lf_roll3", "lf_roll7"]
    df = df.dropna(subset=weather + fires + [PM_COL]).reset_index(drop=True)
    df["log_pm"] = np.log(df[PM_COL])
    years = df["year"].values

    print("=== Season overview (does fire VOLUME track smog LEVEL across years?) ===")
    over = df.groupby("year").agg(total_fires=(FIRE_COL, "sum"),
                                  fires_per_day=(FIRE_COL, "mean"),
                                  mean_pm25=(PM_COL, "mean"),
                                  median_pm25=(PM_COL, "median"))
    print(over.round(1).to_string(), "\n")

    anom = season_anomalies(df, ["log_pm"] + fires + weather)
    anom["diwali_window"] = df["diwali_window"].values

    print("=== Block-bootstrap correlation: fire anomaly vs log-PM2.5 anomaly (pooled) ===")
    for col in fires:
        lo, med, hi = block_bootstrap_corr(anom, col, "log_pm", years)
        print(f"  {col:9s} r = {med:.2f}   95% CI [{lo:.2f}, {hi:.2f}]")
    print("  (If a CI includes 0, the apparent link could be autocorrelation.)\n")

    models = {
        "diwali only (baseline)": ["diwali_window"],
        "weather anomalies": weather + ["diwali_window"],
        "fire anomalies": fires + ["diwali_window"],
        "fires + weather anomalies": fires + weather + ["diwali_window"],
    }
    rows = []
    for name, cols in models.items():
        r2s = loso_anomaly(anom, years, cols)
        rows.append({"model": name, **{f"R2_{y}": round(v, 3) for y, v in zip(sorted(np.unique(years)), r2s)},
                     "mean_R2": round(float(np.mean(r2s)), 3)})
    print("=== Leave-one-season-out R2 on log-PM2.5 ANOMALIES (seasonal ramp removed) ===")
    print(pd.DataFrame(rows).to_string(index=False))
    print("\nFires+weather vs weather alone = what fires add beyond weather, within a season.")

    m = make_model(years)
    cols = fires + weather + ["diwali_window"]
    m.fit(anom[cols], anom["log_pm"])
    coefs = pd.Series(m[-1].coef_, index=cols).sort_values(key=abs, ascending=False)
    print("\nStandardized coefficients (fires+weather anomaly model, all seasons):")
    print(coefs.round(3).to_string())


if __name__ == "__main__":
    main()
