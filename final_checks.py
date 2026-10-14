"""
Final checks before the findings are treated as settled.

Run from repo root (same folder as stubble_pm25_phase2_v2.py / _v3.py):
    python final_checks.py

Part A: re-computes the numbers quoted in the docs and dashboard and compares them.
Part B: stress-tests the main conclusion ("fires add little beyond season and weather")
        under alternative choices. Nothing here changes any file.
"""
import numpy as np
import pandas as pd

import stubble_pm25_phase2_v2 as v2
import stubble_pm25_phase2_v3 as v3

PM, FIRE = v2.PM_COL, v2.FIRE_COL
results = []


def check(name, got, expected, tol):
    ok = abs(got - expected) <= tol
    results.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {name:46s} got {got:9.3f}   quoted {expected:9.3f}")


def prepared(df):
    """Same preparation as v3.main(); returns (df, fires, weather)."""
    sets = v2.feature_sets(df)
    weather = [c for c in sets["C. calendar + weather"] if c not in v3.CALENDAR]
    fires = ["lf", "lf_roll3", "lf_roll7"]
    return df, fires, weather


def increment(df, fires, weather, deg=2):
    """Mean leave-one-season-out R2 on PM2.5 anomalies: weather only vs fires + weather."""
    d = df.dropna(subset=fires + weather + [PM]).reset_index(drop=True)
    d["log_pm"] = np.log(d[PM])
    years = d["year"].values
    anom = v3.season_anomalies(d, ["log_pm"] + fires + weather, deg=deg)
    anom["diwali_window"] = d["diwali_window"].values
    w = np.mean(v3.loso_anomaly(anom, years, weather + ["diwali_window"]))
    fw = np.mean(v3.loso_anomaly(anom, years, fires + weather + ["diwali_window"]))
    return w, fw, fw - w


def main():
    base = v2.build_features(v2.load())

    # ---------------- Part A: quoted numbers ----------------
    print("PART A: do the quoted numbers reproduce?\n")
    raw = v2.load()
    print(" Fire totals per season")
    for yr, exp in {2022: 36310, 2023: 25346, 2024: 7997, 2025: 3430}.items():
        check(f"fires {yr}", raw.loc[raw["year"] == yr, FIRE].sum(), exp, 0.5)
    print(" Season mean PM2.5 (all days, as on the Seasons tab)")
    for yr, exp in {2022: 132.7, 2023: 161.8, 2024: 175.8, 2025: 156.9}.items():
        check(f"mean PM2.5 {yr}", raw.loc[raw["year"] == yr, PM].mean(), exp, 0.06)

    sets = v2.feature_sets(base)
    cols_all = sorted({c for v in sets.values() for c in v})
    d2 = base.dropna(subset=cols_all + [PM]).reset_index(drop=True)
    print(" Leave-one-season-out ablation, mean R2 (Models tab, left)")
    quoted = {"A. calendar baseline": 0.276, "B. calendar + fires": 0.275, "C. calendar + weather": 0.179,
              "D. calendar + fires + weather": 0.257, "E. calendar + yesterday PM2.5": 0.650,
              "F. everything + yesterday PM2.5": 0.637}
    for name, cols in sets.items():
        check(name, v2.loso_eval(d2, cols)["r2"].mean(), quoted[name], 0.002)

    df, fires, weather = prepared(base)
    d3 = df.dropna(subset=fires + weather + [PM]).reset_index(drop=True)
    d3["log_pm"] = np.log(d3[PM])
    years = d3["year"].values
    anom = v3.season_anomalies(d3, ["log_pm"] + fires + weather)
    anom["diwali_window"] = d3["diwali_window"].values
    print(" Within-season anomaly models, mean R2 (Models tab, right)")
    for name, cols, exp in [("fires only", fires + ["diwali_window"], -0.030),
                            ("weather only", weather + ["diwali_window"], 0.133),
                            ("fires + weather", fires + weather + ["diwali_window"], 0.139)]:
        check(name, np.mean(v3.loso_anomaly(anom, years, cols)), exp, 0.002)
    lo, med, hi = v3.block_bootstrap_corr(anom, "lf", "log_pm", years)
    print(" Block-bootstrap correlation, same-day fires (quoted r=0.31, CI 0.13-0.47)")
    check("r median", med, 0.31, 0.02)
    check("CI low", lo, 0.13, 0.03)
    check("CI high", hi, 0.47, 0.03)

    print(f"\n Part A: {sum(results)} of {len(results)} checks passed.\n")

    # ---------------- Part B: robustness ----------------
    print("PART B: does 'fires add little beyond weather' survive other choices?")
    print(" (increment = mean R2 of fires+weather minus weather-only, on within-season anomalies)\n")
    rows = []

    def add(label, df_, fires_, weather_, deg=2):
        w, fw, inc = increment(df_, fires_, weather_, deg)
        rows.append((label, w, fw, inc))

    add("baseline (quadratic detrend)", df, fires, weather)
    for deg in (1, 3):
        add(f"detrend degree {deg}", df, fires, weather, deg)

    for yr in sorted(df["year"].unique()):
        sub = df[df["year"] != yr].reset_index(drop=True)
        try:
            add(f"drop season {yr}", sub, fires, weather)
        except Exception as e:      # tiny folds can fail
            print(f"  (skipped drop {yr}: {e})")

    if "avg_frp" in df.columns:
        df_f = df.copy()
        df_f["lfrp"] = np.log1p(df_f[FIRE] * df_f["avg_frp"].fillna(0))
        df_f["lfrp_roll3"] = df_f.groupby("year")["lfrp"].transform(lambda s: s.rolling(3, min_periods=3).mean())
        df_f["lfrp_roll7"] = df_f.groupby("year")["lfrp"].transform(lambda s: s.rolling(7, min_periods=7).mean())
        add("fire intensity (FRP sum) instead of count", df_f, ["lfrp", "lfrp_roll3", "lfrp_roll7"], weather)

    orig = list(v2.DIWALI)
    for shift in (-1, 1):
        v2.DIWALI = [(pd.Timestamp(x) + pd.Timedelta(days=shift)).strftime("%Y-%m-%d") for x in orig]
        dshift, f2, w2 = prepared(v2.build_features(v2.load()))
        add(f"Diwali dates shifted {shift:+d} day", dshift, f2, w2)
    v2.DIWALI = orig

    print(f" {'variant':46s} {'weather':>9s} {'fires+wx':>9s} {'increment':>10s}")
    stable = []
    for label, w, fw, inc in rows:
        unstable = abs(w) > 1 or abs(fw) > 1
        print(f" {label:46s} {w:9.3f} {fw:9.3f} {inc:+10.3f}" + ("   UNSTABLE fold, ignore" if unstable else ""))
        if not unstable:
            stable.append(inc)
    if stable:
        hurt = sum(1 for x in stable if x < -0.02)
        print(f"\n Largest gain from adding fires in any stable variant: {max(stable):+.3f}")
        print(f" Variants where adding fires made predictions worse (overfitting): {hurt} of {len(stable)}")

    # level model on log(PM2.5)
    v2.LOG_TARGET = True
    sets_l = v2.feature_sets(base)
    cols_l = sorted({c for v in sets_l.values() for c in v})
    dl = base.dropna(subset=cols_l + [PM]).reset_index(drop=True)
    r = {k: v2.loso_eval(dl, c)["r2"].mean() for k, c in sets_l.items()}
    v2.LOG_TARGET = False
    print("\n Level model with log(PM2.5) target:")
    print(f"   fires over calendar (B-A) = {r['B. calendar + fires'] - r['A. calendar baseline']:+.3f}    "
          f"fires over weather (D-C) = {r['D. calendar + fires + weather'] - r['C. calendar + weather']:+.3f}")

    print("\n Read it: if the largest gain stays small (roughly under +0.03), the 'little added power")
    print(" beyond season and weather' wording is safe. If one variant shows a clearly larger gain,")
    print(" tell me which one and we revisit that sentence.")


if __name__ == "__main__":
    main()
