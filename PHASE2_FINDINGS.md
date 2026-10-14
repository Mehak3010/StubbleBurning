# Phase 2 Findings: Audit, Corrections, and Weather Analysis

**Question (unchanged):** Does Punjab/Haryana crop-residue burning predict Delhi-NCR's daily PM2.5?

**Study area:** NOAA-20 fire detections inside a fixed bounding box of 74.5–76.0°E, 29.0–31.5°N, used identically for all four seasons. By area it is roughly two-thirds Punjab, a quarter Haryana and 9% north-west Rajasthan, covering much of central and western Punjab and part of north-west Haryana; northern Punjab and eastern Haryana are outside it, so counts understate regional burning. Year-to-year comparisons are like for like within the box.

Phase 1 (`PHASE1_FINDINGS.md`) is kept as the original record of what was found and published first. Phase 2 re-audited the pipeline, added weather data, and re-tested the question with stricter methods. **Where the two documents disagree, this one is current.**

---

## Summary

1. **The pipeline was audited and the fire table rebuilt** (below), and Phase 1's figures were recomputed on the updated data.
2. **Some Phase 1 observations hold:** 2025 had about 10x fewer fires than 2022 (36,310 vs 3,430 detections), and Delhi's smog was not lower for it.
3. **Several Phase 1 claims are not supported** once the data is corrected and weather is added: the 12-36 hour lag, the "~48% explained by fires" figure, and the what-if simulator's absolute predictions.
4. **Fire counts carry a modest, model-dependent signal.** In the main within-season analysis, daily fire counts add little predictive power beyond the seasonal pattern and basic weather, and weather anomalies explain more than fire anomalies do. But the size of the fire contribution depends on modeling choices, from about zero to a clear gain (see the robustness section), and it is positive in some seasons and absent in others.
5. **This does not show that stubble burning doesn't matter.** Daily NOAA-20 fire counts compared against a citywide PM2.5 average are a weak proxy for smoke reaching Delhi. The honest conclusion is that this dataset cannot isolate the stubble contribution.

---

## 1. Data audit

Phase 2 began with a routine audit of the pipeline. The fire columns in the merged table were rebuilt from the raw FIRMS exports with `refresh_fires.py`, which also validates coverage and stops the pipeline if any season has missing or zero fire data. This changed the 2024 and 2025 fire counts, and Phase 1's figures were recomputed on the rebuilt table (section 2).

Detections after the rebuild (NOAA-20 VIIRS, Oct-Nov, study box):

| Season | Detections |
|---|---|
| 2022 | 36,310 |
| 2023 | 25,346 |
| 2024 | 7,997 |
| 2025 | 3,430 |

The 2025 vs 2024 drop is about 57%, consistent with the roughly 54% reduction reported by the Punjab Pollution Control Board (a statewide figure; ours covers only the study box).

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

Lag correlations (corrected), lags 0-7 days: 0.374, 0.354, 0.300, 0.254, 0.203, 0.175, 0.176, 0.207. The correlation fades over the first four days and then levels off around 0.2 rather than continuing to decay.

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

- Adding fires to the calendar baseline gives no gain on average on the raw PM2.5 scale (0.276 vs 0.275). On a log(PM2.5) target the same comparison gives about +0.07 (0.129 to 0.198). Adding fires on top of weather improves mean R² by about +0.08 on both scales (raw 0.179 to 0.257; log 0.200 to 0.279). See the robustness section.
- **Read the +0.08 with its baseline in mind.** The +0.08 is an increment over a weather model that is itself weaker than the calendar baseline on the raw scale (0.179 vs 0.276), and fires + weather (0.257) also stays below the calendar baseline there. On the raw scale, neither weather nor fires beats the calendar baseline on average. On the log scale both help (0.129 for calendar alone, 0.279 with fires and weather).
- The +0.08 is a mean across the four held-out seasons, not the 2025 test result, and it is uneven across seasons (see section 6b).
- Next-day forecasting is dominated by persistence (E); fires and weather do not improve on it (F).
- Four seasons of about 55 usable days each is a small sample; per-season values are noisy.

---

## 5. Within-season analysis (seasonal ramp removed)

Each season's quadratic Oct-Nov trend was removed from log PM2.5, fire activity and weather, leaving day-to-day anomalies.

**Season overview.** Two sets of averages appear in this project because lag features consume the first days of each season. The all-days figures (61 days per season) are used in the README, the dashboard and the public post; the 55-day figures are the days actually usable in the models.

| Season | Fires/day (61 days) | Mean PM2.5 (61 days) | Fires/day (55 days) | Mean PM2.5 (55 days) | Median PM2.5 (55 days) |
|---|---|---|---|---|---|
| 2022 | 595 | 132.7 | 657 | 140.5 | 128.0 |
| 2023 | 416 | 161.8 | 457 | 172.8 | 146.0 |
| 2024 | 131 | 175.8 | 144 | 189.2 | 181.0 |
| 2025 | 56 | 156.9 | 62 | 168.7 | 175.1 |

The ordering is the same under both. The season with the most fires (2022) had the lowest mean PM2.5. With four seasons this is not proof, but it does not support "more fires, worse smog" at the season level. The headline comparison used publicly is 2025 vs 2022 on all 61 days: 156.9 vs 132.7 µg/m³ (about 157 vs 133).

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

In this setup weather explains more day-to-day variation than fires do, and adding fires to weather moves mean R² only from 0.133 to 0.139, which is within noise. This depends on how the seasonal ramp is removed (see the robustness section). Weather coefficients have physically sensible signs (upwind alignment positive; wind speed and ventilation negative).

---

## 6. Status of the original public claims

| Original claim | Status |
|---|---|
| Fires predict smog with a ~12-36 hour lag | **Not supported.** Daily data cannot resolve hours, and the lag decay is largely seasonality |
| A model explains ~48% of daily PM2.5 using only fire data, tested on an unseen 2025 season | **Superseded.** Recomputed on corrected data (Ridge R² 0.545). The model includes day of season, and a calendar-only baseline reaches similar skill on 2025, so this is not a fire-only figure |
| 2025 had 10x fewer fires than 2022, yet Delhi still choked | **Confirmed.** 36,310 vs 3,430 detections; mean PM2.5 of about 157 vs 133 µg/m³ over all 61 days of each season |
| Fires are a big piece of the story | **Not established** by this data |
| Wind and weather are missing pieces | **Supported in the main within-season analysis** (weather anomalies outperform fire anomalies), though that comparison is sensitive to modeling choices, and in the level models weather alone does not beat the calendar baseline on the raw scale |
| What-if simulator: 800 fires/day sustained for a week pushes Delhi into "Very Poor" air | **Retracted.** It assumed a stable cross-year relationship between fire count and PM2.5 level, which the data does not support |

---

## 6b. Robustness of the main result

The within-season question was re-run under alternative choices (`final_checks.py`). "Gain" is the change in mean leave-one-season-out R² on PM2.5 anomalies when fire features are added to weather.

| Variant | Weather only | Fires + weather | Gain from fires |
|---|---|---|---|
| Quadratic detrend (main analysis) | 0.133 | 0.139 | +0.006 |
| Linear detrend | 0.219 | 0.456 | +0.236 |
| Cubic detrend | -0.059 | -0.056 | +0.003 |
| Drop 2022 | 0.015 | 0.011 | -0.004 |
| Drop 2023 | 0.078 | 0.073 | -0.005 |
| Drop 2024 | 0.152 | 0.221 | +0.069 |
| Drop 2025 | 0.109 | 0.138 | +0.029 |
| Fire intensity (FRP sum) instead of count | 0.133 | 0.129 | -0.004 |
| Diwali dates shifted -1 day | 0.145 | 0.153 | +0.008 |
| Diwali dates shifted +1 day | 0.144 | 0.149 | +0.005 |

Level models (not anomalies) on a log(PM2.5) target, mean R²: calendar 0.129, + fires 0.198, + weather 0.200, + fires + weather 0.279. Gain from fires on top of weather by held-out season: +0.03 (2022), +0.28 (2023), +0.10 (2024), -0.09 (2025). Forecast models using yesterday's PM2.5 are unstable on this scale (one fold at R² of -1.17) and are not used.

**What this means.**
- The fire contribution is small in the main setup but not zero, and it moves with modeling choices: roughly +0.00 to +0.07 in most variants, and +0.24 with a linear seasonal detrend.
- A linear detrend leaves seasonal curvature that fires and PM2.5 may share, so the larger value is probably not a pure day-to-day effect. A cubic detrend may remove genuine fire-driven variation. Neither choice is clearly correct.
- The gain is uneven across seasons: clear in 2023 and 2024, small in 2022 and negative in 2025.
- The data therefore support "fire counts add a modest, fragile signal beyond season and weather", not "fires matter little" and not "fires explain most of the variation".

---

## 7. Limitations

- **Partial regional coverage.** The fire box omits parts of the burning region (northern Punjab and eastern Haryana, and it includes some north-west Rajasthan). If the geographic mix of burning shifted between years, counts could understate those shifts. Re-running with full-region coverage is a Phase 3 item.
- **Seasonal shape is hard to separate from fires.** Fires and PM2.5 both rise and fall through Oct-Nov, and how that shape is removed changes the estimated fire contribution from about zero to substantial.
- **Four seasons, about 220 usable days.** Results are sensitive to individual years.
- **Detection undercount is possible.** NOAA-20 crosses over in the early afternoon; if a large share of burning happens later in the day, daily counts understate activity, and that share may vary by year. This is a hypothesis to verify against the literature, not something shown here.
- **Counts ignore location and size.** A count does not capture distance to Delhi, fire size, or whether the wind carried smoke toward the city. FRP was available but only used in early versions.
- **Citywide PM2.5 average.** OpenAQ readings are averaged across sensors, and the set of reporting sensors may differ between years (not yet checked). This could affect the season-average comparison between 2022 and 2025. Local sources dominate Delhi's winter air.
- **Daily resolution.** Smoke transport operates on hourly timescales.
- **Unverified inputs.** Diwali dates were entered by hand and should be checked against an official calendar.
- **Correlation, not causation**, throughout.

---

## 8. Reproducing Phase 2

```bash
python refresh_fires.py                 # rebuild fire columns (validates coverage per season)
python fetch_weather.py                 # Open-Meteo, no API key
python merge_weather.py                 # -> master_with_weather.csv
python stubble_pm25_model.py            # Phase 1 method on corrected data
python stubble_pm25_phase2_v2.py        # ablation, leave-one-season-out
python stubble_pm25_phase2_v3.py        # within-season anomalies, block bootstrap
python final_checks.py                  # re-checks quoted numbers; robustness variants (section 6b)
python export_dashboard_data.py         # writes dashboard/src/data.js
```

Raw and processed datasets remain excluded from the repository under the original data-use terms.

---

## 9. Suggested Phase 3

- Re-download FIRMS for a wider box (about 73.8–77.6°E, 28.3–32.6°N) and re-run the full pipeline to test whether the conclusions change.
- Weight fires by distance and upwind direction; sum FRP instead of counting detections.
- Back-trajectory modeling (for example HYSPLIT) to estimate smoke arrival at Delhi.
- Station-level or hourly PM2.5 instead of a citywide daily mean.
- Check sensor coverage consistency across years.
- Verify Diwali dates against an official calendar.
- Extend the series to more seasons, and test the satellite overpass-timing question.
- Rebuild the dashboard around within-season, relative comparisons instead of absolute what-if predictions.