# Phase 2 Findings: Audit, Corrections, and Weather Analysis

**Question (unchanged):** Does Punjab/Haryana crop-residue burning predict Delhi-NCR's daily PM2.5?

Phase 1 (`PHASE1_FINDINGS.md`) is kept as the original record of what was found and published first. Phase 2 re-audited the pipeline, found two data bugs that affected Phase 1's headline numbers, added weather data, and re-tested the question with stricter methods. **Where the two documents disagree, this one is current.**

---

## Summary

1. **Two data problems were found and fixed** (below), and Phase 1's figures were recomputed on the corrected data.
2. **Some Phase 1 observations hold:** 2025 had about 10x fewer fires than 2022 (36,310 vs 3,430 detections), and Delhi's smog was not lower for it.
3. **Several Phase 1 claims are not supported** once the data is corrected and weather is added: the 12-36 hour lag, the "~48% explained by fires" figure, and the what-if simulator's absolute predictions.
4. **Within a season, daily fire counts add little predictive power** beyond the seasonal pattern and basic weather. Weather anomalies explain more than fire anomalies do.
5. **This does not show that stubble burning doesn't matter.** Daily NOAA-20 fire counts compared against a citywide PM2.5 average are a weak proxy for smoke reaching Delhi. The honest conclusion is that this dataset cannot isolate the stubble contribution.

---

## 1. Data corrections

| Issue | Effect | Fix |
|---|---|---|
| Two identical 2024 FIRMS files (`fire_archive_J1V-C2_785706.csv` and `..._785707.csv`) were both loaded and concatenated | 2024 fire counts were double-counted (7,997 duplicate detections) | De-duplicate on latitude, longitude, date and time |
| `master_dashboard_data.csv` contained **no 2025 fire data** (all 61 days NaN), and the model script filled missing fires with 0 | At the time of the audit, 2025 fire columns were empty in the master table, and the model script fills missing fires with 0, which would turn a missing season into zero fires. Whether the master was already in this state when the original Phase 1 figures were produced is unconfirmed (the model script's notes cite 2,942 detections for 2025) | Rebuilt fire columns with `refresh_fires.py`; added guards that stop the pipeline if a season has missing or zero fires |

Corrected detections (NOAA-20 VIIRS, Oct-Nov, Punjab/Haryana):

| Season | Detections |
|---|---|
| 2022 | 36,310 |
| 2023 | 25,346 |
| 2024 | 7,997 |
| 2025 | 3,430 |

The 2025 vs 2024 drop is about 57%, consistent with the roughly 54% reduction reported by the Punjab Pollution Control Board.

---

## 2. Phase 1 re-run on corrected data

Same method as Phase 1 (train 2022-2024, test on 2025):

| | Phase 1 (as published) | Corrected |
|---|---|---|
| Fire / PM2.5 correlation, lag 0 | 0.435 | 0.374 |
| Ridge R² | 0.481 | 0.545 |
| Random Forest R² | 0.462 | 0.560 |
| XGBoost R² | 0.415 | 0.544 |
| Ridge MAE | 39.0 | 36.1 |

Lag correlations (corrected): 0.374, 0.354, 0.300, 0.254, 0.203, 0.175, 0.176, 0.207 for lags 0-7 days.

**Why these numbers should not be read as "fires explain ~55%":** the Phase 1 model included `day_of_season`, and PM2.5 rises steadily through Oct-Nov. A baseline using only calendar features (day of season, Diwali window, weekend) reaches R² of about 0.44-0.50 on 2025 by itself. The model's apparent skill is mostly the seasonal ramp.

---

## 3. Weather data added

- **Source:** Open-Meteo historical archive, hourly, aggregated to daily (IST).
- **Locations:** Delhi (28.61, 77.21), Karnal (29.69, 76.99), Ludhiana (30.90, 75.85).
- **Variables:** wind speed and direction (as u/v components), temperature, humidity, precipitation, boundary layer height.
- **Derived:** a wind *alignment* score (positive when wind carries air from the Punjab burning region toward Delhi) and a ventilation index (boundary layer height x wind speed).
- **Confounder control:** Diwali window flag (+/-2 days), day of season, weekend flag.

---

## 4. Does fire add predictive power? (leave-one-season-out)

Each season was held out in turn. R² on the held-out season; every model includes the calendar baseline so fire and weather effects appear as increments.

| Model | 2022 | 2023 | 2024 | 2025 | Mean R² |
|---|---|---|---|---|---|
| A. Calendar baseline | -0.094 | 0.394 | 0.300 | 0.502 | 0.276 |
| B. + fires | -0.250 | 0.594 | 0.347 | 0.407 | 0.275 |
| C. + weather | -0.369 | 0.428 | 0.284 | 0.375 | 0.179 |
| D. + fires + weather | -0.139 | 0.481 | 0.259 | 0.427 | 0.257 |
| E. + yesterday's PM2.5 | 0.547 | 0.716 | 0.600 | 0.736 | 0.650 |
| F. everything + yesterday's PM2.5 | 0.468 | 0.750 | 0.617 | 0.713 | 0.637 |

- Adding fires to the calendar baseline gives no gain on average (0.276 vs 0.275).
- Next-day forecasting is dominated by persistence (E); fires and weather do not improve on it (F).
- Four seasons of about 55 usable days each is a small sample; per-season values are noisy.

---

## 5. Within-season analysis (seasonal ramp removed)

Each season's quadratic Oct-Nov trend was removed from log PM2.5, fire activity and weather, leaving day-to-day anomalies.

**Season overview** (55 usable days per season after lag features):

| Season | Fires/day | Mean PM2.5 | Median PM2.5 |
|---|---|---|---|
| 2022 | 657 | 140.5 | 128.0 |
| 2023 | 457 | 172.8 | 146.0 |
| 2024 | 144 | 189.2 | 181.0 |
| 2025 | 62 | 168.7 | 175.1 |

The season with the most fires had the lowest mean PM2.5. With four seasons this is not proof, but it does not support "more fires, worse smog" at the season level.

**Block-bootstrap correlation** (7-day blocks, to respect autocorrelation), fire anomaly vs log-PM2.5 anomaly:

| Fire feature | r | 95% CI |
|---|---|---|
| Same-day (log) | 0.31 | [0.13, 0.47] |
| 3-day mean | 0.25 | [-0.01, 0.47] |
| 7-day mean | -0.01 | [-0.26, 0.22] |

An earlier, simpler check (linear detrend, no bootstrap) showed correlations of 0.5-0.7. Those were inflated by shared seasonal curvature and autocorrelation and should not be cited.

**Predicting PM2.5 anomalies in a held-out season (R²):**

| Model | 2022 | 2023 | 2024 | 2025 | Mean |
|---|---|---|---|---|---|
| Diwali flag only | 0.000 | -0.001 | -0.001 | -0.085 | -0.022 |
| Weather anomalies | 0.180 | 0.178 | 0.016 | 0.155 | 0.133 |
| Fire anomalies | 0.002 | -0.105 | -0.001 | -0.014 | -0.030 |
| Fires + weather | 0.252 | 0.188 | -0.042 | 0.158 | 0.139 |

Weather explains more day-to-day variation than fires do. Adding fires to weather moves mean R² from 0.133 to 0.139, which is within noise. Weather coefficients have physically sensible signs (upwind alignment positive; wind speed and ventilation negative).

---

## 6. Status of the original public claims

| Original claim | Status |
|---|---|
| Fires predict smog with a ~12-36 hour lag | **Not supported.** Daily data cannot resolve hours, and the lag decay is largely seasonality |
| A model explains ~48% of daily PM2.5 using only fire data, tested on an unseen 2025 season | **Superseded.** Recomputed on corrected data (Ridge R² 0.545). The model includes day of season, and a calendar-only baseline reaches similar skill on 2025, so this is not a fire-only figure |
| 2025 had 10x fewer fires than 2022, yet Delhi still choked | **Confirmed.** 36,310 vs 3,430 detections; mean PM2.5 of 169 vs 140 |
| Fires are a big piece of the story | **Not established** by this data |
| Wind and weather are missing pieces | **Supported.** Weather anomalies outperform fire anomalies |
| What-if simulator: 800 fires/day sustained for a week pushes Delhi into "Very Poor" air | **Retracted.** It assumed a stable cross-year relationship between fire count and PM2.5 level, which the data does not support |

---

## 7. Limitations

- **Four seasons, about 220 usable days.** Results are sensitive to individual years.
- **Detection undercount is possible.** NOAA-20 crosses over in the early afternoon; if a large share of burning happens later in the day, daily counts understate activity, and that share may vary by year. This is a hypothesis to verify against the literature, not something shown here.
- **Counts ignore location and size.** A count does not capture distance to Delhi, fire size, or whether the wind carried smoke toward the city. FRP was available but only used in early versions.
- **Citywide PM2.5 average.** OpenAQ readings are averaged across sensors, and the set of reporting sensors may differ between years (not yet checked). Local sources dominate Delhi's winter air.
- **Daily resolution.** Smoke transport operates on hourly timescales.
- **Unverified inputs.** Diwali dates were entered by hand and should be checked against an official calendar.
- **Correlation, not causation**, throughout.

---

## 8. Reproducing Phase 2

```bash
python refresh_fires.py                 # rebuild fire columns (dedupes, guards missing seasons)
python fetch_weather.py                 # Open-Meteo, no API key
python merge_weather.py                 # -> master_with_weather.csv
python stubble_pm25_model.py            # Phase 1 method on corrected data
python stubble_pm25_phase2_v2.py        # ablation, leave-one-season-out
python stubble_pm25_phase2_v3.py        # within-season anomalies, block bootstrap
```

Raw and processed datasets remain excluded from the repository under the original data-use terms.

---

## 9. Suggested Phase 3

- Weight fires by distance and upwind direction; sum FRP instead of counting detections.
- Back-trajectory modeling (for example HYSPLIT) to estimate smoke arrival at Delhi.
- Station-level or hourly PM2.5 instead of a citywide daily mean.
- Check sensor coverage consistency across years.
- Extend the series to more seasons, and test the satellite overpass-timing question.
- Rebuild the dashboard around within-season, relative comparisons instead of absolute what-if predictions.
