# 🔥 Stubble Burning → Delhi Smog

**Does Punjab/Haryana crop-residue burning predict Delhi-NCR's PM2.5?**

A data pipeline, predictive models, and an interactive dashboard analyzing four
autumn burning seasons (2022–2025) of NASA satellite fire data against
Delhi-NCR air quality readings, built to answer one question with real
numbers instead of received wisdom.

---

**Study area:** NOAA-20 fire detections inside a fixed bounding box of 74.5–76.0°E, 29.0–31.5°N, used identically for all four seasons. This approximately covers central and western Punjab and part of north-west Haryana; northern Punjab and eastern Haryana are outside it, so counts understate regional burning. Year-to-year comparisons are like for like within the box.

---

## Findings

**Data:** NASA FIRMS VIIRS (NOAA-20) fire detections over the study area,
Oct–Nov **2022–2025** (4 seasons), merged with Delhi-NCR daily PM2.5 (OpenAQ).
244 daily records after cleaning.

**Fire activity and smog move together over following days.** Same-day fire
activity correlates with Delhi PM2.5 at **r = 0.37**, decaying over the next
week. That fits smoke arriving within days of burning, though daily data
cannot resolve a specific transport time, and part of the pattern reflects
both series rising through the season.

| Lag (days)  | 0     | 1     | 2     | 3     | 4     | 7     |
| ----------- | ----- | ----- | ----- | ----- | ----- | ----- |
| Correlation | 0.374 | 0.354 | 0.300 | 0.254 | 0.203 | 0.207 |

**Models reach R² ≈ 0.54–0.56** on a held-out season, trained on 2022–2024 and
tested on the fully held-out 2025 season (a genuine future-year test, not an
interpolated split). These models include day-of-season alongside fire
features, so the R² reflects the seasonal rise in PM2.5 as well as fire activity.

| Model                          | R²        | MAE  | RMSE |
| ------------------------------ | --------- | ---- | ---- |
| Ridge (regularized linear)     | 0.545     | 36.1 | 49.1 |
| **Random Forest**              | **0.560** | 36.8 | 48.3 |
| XGBoost                        | 0.544     | 38.5 | 49.1 |

**2025's fire count genuinely collapsed**: 3,430 detections vs. 36,310 in
2022 (about 10x fewer), corroborated by independently reported Punjab Pollution
Control Board figures (a 54% drop vs. 2024), not a data gap. Delhi's 2025 smog was not lower than 2022's, which is why weather and other sources matter.

**Phase 2 adds weather** (wind, temperature, humidity, boundary layer height)
and re-tests the question with stricter methods. See
[`PHASE2_FINDINGS.md`](PHASE2_FINDINGS.md) for results and
[`PHASE1_FINDINGS.md`](PHASE1_FINDINGS.md) for the original analysis and data notes.

---

## What's in here

```
.
├── PHASE1_FINDINGS.md          # Phase 1: methodology, findings, data notes
├── PHASE2_FINDINGS.md          # Phase 2: weather, ablations, within-season analysis
├── prepare_dashboard_data.py   # Merges NASA FIRMS fire data + OpenAQ PM2.5 into one daily table
├── stubble_pm25_model.py       # Phase 1: feature engineering + Ridge / RF / XGBoost comparison
├── refresh_fires.py            # Rebuilds fire columns from FIRMS files (dedupes, checks coverage)
├── fetch_weather.py            # Phase 2: daily weather from Open-Meteo (no API key)
├── merge_weather.py            # Phase 2: merges weather into the master table
├── stubble_pm25_phase2_v2.py   # Phase 2: ablation, leave-one-season-out CV
├── stubble_pm25_phase2_v3.py   # Phase 2: within-season anomalies, block bootstrap
└── dashboard/                  # React dashboard (data embedded at build time)
```

## Data sources

- **Fire detections:** [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) VIIRS,
  NOAA-20/JPSS-1 (J1V), study box 74.5–76.0°E / 29.0–31.5°N, Oct–Nov 2022–2025
- **Air quality:** [OpenAQ](https://openaq.org/) v3 API, Delhi-NCR PM2.5 sensors
- **Weather (Phase 2):** [Open-Meteo](https://open-meteo.com/) historical archive

> **Note:** The raw and processed datasets (`AQI Datasets/`, `*.csv`) are **not
> included in this repository**. They were shared under a data-use permission for
> this project and are excluded via `.gitignore`. To reproduce the pipeline,
> request access to the same FIRMS export and an OpenAQ API key.

## Running the pipeline

```
pip install pandas requests scikit-learn xgboost numpy

# Phase 1
export OPENAQ_API_KEY="your-key-here"
python prepare_dashboard_data.py     # merge fire + air quality into master_dashboard_data.csv
python stubble_pm25_model.py         # features, models, held-out 2025 evaluation

# Phase 2
python fetch_weather.py              # Open-Meteo, no key needed
python merge_weather.py              # -> master_with_weather.csv
python stubble_pm25_phase2_v2.py
python stubble_pm25_phase2_v3.py
```

## Running the dashboard

```
cd dashboard
npm install
npm run dev
```

## Methodology notes worth knowing

- Only NOAA-20 (J1V) fire detections are used, never mixed with S-NPP (SV),
  so fire counts are comparable year over year.
- The pipeline de-duplicates detections and stops if any season has missing or
  zero fire data, rather than filling the gap.
- Models are evaluated on a **time-based split** (train 2022–2024, test on the
  held-out 2025 season), not a random split.
- Phase 1 models include day-of-season, so reported R² reflects the seasonal
  rise in PM2.5 as well as fire activity. Phase 2 separates the two.

---

*See [`PHASE1_FINDINGS.md`](PHASE1_FINDINGS.md) and
[`PHASE2_FINDINGS.md`](PHASE2_FINDINGS.md) for the full write-ups.*
