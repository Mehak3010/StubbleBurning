# Phase 1: Does Punjab Stubble Burning Predict Delhi's PM2.5?

**Data:** NASA FIRMS VIIRS (NOAA-20) fire detections over Punjab/Haryana, Oct–Nov **2022–2025** (4 seasons), merged with Delhi-NCR daily PM2.5 (OpenAQ). 244 daily records after cleaning.

**Study area:** NOAA-20 fire detections inside a fixed bounding box of 74.5–76.0°E, 29.0–31.5°N, used identically for all four seasons. This approximately covers central and western Punjab and part of north-west Haryana; northern Punjab and eastern Haryana are outside it, so counts understate regional burning. Year-to-year comparisons are like for like within the box.

## Data quality notes
- Two 2024 FIRMS exports (`fire_archive_J1V-C2_785706.csv` and `_785707.csv`) are identical (7,997 rows each, same dates). Duplicates are removed by de-duplicating on location, date and time.
- All four seasons use a single satellite source (NOAA-20), so fire counts are comparable year over year.
- The pipeline checks fire coverage for every season before modeling and stops if a season has missing or zero fire data. Days with no detections are treated as zero-fire days.
- **2025 fire counts are genuinely, dramatically lower** than prior seasons. This is real, not a data gap:

  | Season | Total fires detected (Oct–Nov) |
  |---|---|
  | 2022 | 36,310 |
  | 2023 | 25,346 |
  | 2024 | 7,997 |
  | **2025** | **3,430** |

  That is a 57% drop vs. 2024 and a 91% drop vs. 2022. It is consistent with independently reported figures: Punjab's Pollution Control Board recorded a **54% drop** in stubble fire cases in 2025 vs. 2024 (5,114 vs. 10,909), and the Union Environment Ministry reported a **90% reduction** vs. 2022, attributed to CRM (crop residue management) machinery subsidies (₹3,120+ crore disbursed since 2018) and stricter enforcement.

## Key finding: fire activity and smog move together over following days

| Lag (days) | Correlation |
|---|---|
| 0 | 0.374 |
| 1 | 0.354 |
| 2 | 0.300 |
| 3 | 0.254 |
| 4 | 0.203 |
| 7 | 0.207 |

Fire activity is positively correlated with Delhi PM2.5: strongest same-day and next-day, and decaying over the following week. That fits smoke arriving within a few days of burning, but daily data cannot resolve a specific transport time, and part of the pattern reflects both series rising through the Oct–Nov season (examined in Phase 2).

## Model performance (trained on 2022–2024, tested on held-out 2025 season)

| Model | R² | MAE | RMSE |
|---|---|---|---|
| Ridge (regularized linear) | 0.545 | 36.1 | 49.1 |
| **Random Forest** | **0.560** | 36.8 | 48.3 |
| XGBoost | 0.544 | 38.5 | 49.1 |

All three models perform similarly (R² ≈ 0.54–0.56) on a genuinely future, out-of-sample season rather than an interpolated one. The models include day-of-season alongside the fire features, so this R² reflects the seasonal rise in PM2.5 as well as fire activity. It leaves substantial room for wind, temperature inversion, local emissions and Diwali fireworks, which are not modeled here. Phase 2 adds weather and separates the contributions.

## What drives the prediction
Cumulative 3-day and 7-day fire activity, same-day and lagged fire counts, and day-of-season are the dominant features. Several of these are highly correlated with one another, so individual coefficients should not be interpreted separately.

## Natural next step
Meteorological data (wind speed/direction, temperature, humidity, boundary layer height) is the highest-value addition. Phase 2 adds it; see `PHASE2_FINDINGS.md`.

---
*Revised October 2026: figures updated after a pipeline audit (duplicate 2024 export removed; 2025 fire data fully merged). Corrected analysis and further results are in `PHASE2_FINDINGS.md`.*

Generated files: `stubble_pm25_model.py` (pipeline), `master_dashboard_data.csv`, `cleaned_daily_fire_pm25.csv`, `model_dataset_with_features.csv`.
