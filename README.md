# 🔥 Stubble Burning → Delhi Smog

**Does Punjab/Haryana crop-residue burning predict Delhi-NCR's PM2.5?**

A data pipeline, predictive model, and interactive dashboard analyzing four
autumn burning seasons (2022–2025) of NASA satellite fire data against
Delhi-NCR air quality readings — built to answer one question with real
numbers instead of received wisdom.

---

## Findings

**Data:** NASA FIRMS VIIRS (NOAA-20) fire detections over Punjab/Haryana,
Oct–Nov **2022–2025** (4 seasons), merged with Delhi-NCR daily PM2.5 (OpenAQ).
244 daily records after cleaning.

**Yes — fires predict smog, with a lag.** Same-day/next-day fire activity
correlates with Delhi PM2.5 at **r = 0.44**, decaying over the following
week. That decay shape is consistent with a ~12–36 hour Punjab-to-Delhi
smoke transport window, and it holds across all four seasons.

| Lag (days) | 0 | 1 | 2 | 3 | 7 |
|---|---|---|---|---|---|
| Correlation | 0.435 | 0.398 | 0.335 | 0.291 | 0.251 |

**A Ridge regression explains ~48% of daily PM2.5 variance** using only fire
features, trained on 2022–2024 and tested on the fully held-out 2025 season
(a genuine future-year test, not an interpolated split):

| Model | R² | MAE | RMSE |
|---|---|---|---|
| **Ridge (regularized linear)** | **0.481** | 39.0 | 52.4 |
| Random Forest | 0.462 | 41.1 | 53.3 |
| XGBoost | 0.415 | 43.2 | 55.6 |

**2025's fire count genuinely collapsed** — 3,430 detections vs. 36,310 in
2022 — corroborated by independently reported Punjab Pollution Control Board
figures (a 54% drop vs. 2024), not a data gap. The strongest predictive
features are 3-day and 7-day cumulative fire activity and prior-day fire
count, not same-day count alone, which is itself evidence of real
atmospheric transport rather than coincidence.

**Biggest open gap:** no weather data yet. Wind speed/direction, temperature,
and humidity are the natural next addition — the lag-decay pattern is
indirect evidence that wind-driven transport is the main missing variable.

📄 **Full write-up with data-quality corrections, season-by-season breakdowns,
and feature-importance detail: [`PHASE1_FINDINGS.md`](./PHASE1_FINDINGS.md).**

---

## What's in here

```
.
├── PHASE1_FINDINGS.md          # Full write-up: methodology, findings, caveats
├── prepare_dashboard_data.py   # Merges NASA FIRMS fire data + OpenAQ PM2.5 into one daily table
├── stubble_pm25_model.py       # Feature engineering + Ridge / RF / XGBoost model comparison
└── dashboard/                  # Single-view React dashboard (data embedded at build time)
```

## Data sources

- **Fire detections:** [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) VIIRS,
  NOAA-20/JPSS-1 (J1V), Punjab & Haryana, Oct–Nov 2022–2025
- **Air quality:** [OpenAQ](https://openaq.org/) v3 API, Delhi-NCR PM2.5 sensors

> **Note:** The raw and processed datasets (`AQI Datasets/`, `*.csv`) are
> **not included in this repository**. They were shared under a data-use
> permission for this project and are excluded via `.gitignore`. To
> reproduce the pipeline, request access to the same FIRMS export and an
> OpenAQ API key, then run `prepare_dashboard_data.py` followed by
> `stubble_pm25_model.py`.

## Running the pipeline

```bash
pip install pandas requests scikit-learn xgboost numpy

# 1. Merge fire + air quality data into master_dashboard_data.csv
export OPENAQ_API_KEY="your-key-here"
python prepare_dashboard_data.py

# 2. Engineer features, train models, evaluate on held-out 2025 season
python stubble_pm25_model.py
```

## Running the dashboard

```bash
cd dashboard
npm install
npm run dev
```

## Methodology notes worth knowing

- Only NOAA-20 (J1V) fire detections are used, never mixed with S-NPP (SV),
  so fire counts are comparable year over year.
- Models are evaluated on a genuine **time-based split** — trained on
  2022–2024, tested on the fully held-out 2025 season — not a random or
  interpolated split, so the reported R² reflects real forecasting skill.
- The dominant predictive features are 3-day and 7-day cumulative fire
  activity and prior-day fire count, not same-day fire count alone —
  consistent with a real atmospheric transport lag rather than a
  same-day coincidence.

---

*Phase 1 analysis. See [`PHASE1_FINDINGS.md`](./PHASE1_FINDINGS.md) for the
full data-quality writeup, season-by-season figures, and everything behind
the summary above.*
