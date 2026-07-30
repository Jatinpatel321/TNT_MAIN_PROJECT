# ML Baseline Metrics

**Training run executed:** 2026-07-29T05:25:52Z (UTC)  
**Database:** `localhost:5432/tnt` (production PostgreSQL)  
**Training window:** 90 days  
**Script:** `run_training_and_capture.py` → raw JSON at `docs/training_raw_results.json`

---

> [!CAUTION]
> **ALL five models are LOW CONFIDENCE.** Every model trained on far fewer rows than
> minimum viable thresholds. RMSE = 0.0 and R² = 1.0 across all regression models is
> a definitive sign of overfitting on tiny datasets — these metrics do not reflect real
> generalisation ability. **Treat the heuristic as primary for all planners until
> production data accumulates.**

---

## Summary Table

| Model Type | Status | Winner | Rows Trained | MAE | RMSE | R² / Accuracy | Low-Confidence Flag |
|---|---|---|---|---|---|---|---|
| `eta_prediction` | ✅ success | RandomForest | **26** | 0.000 | 0.000 | 1.000 | ⚠️ YES |
| `demand_forecast` | ✅ success | XGBoost | **28** | 0.000 | 0.000 | 1.000 | ⚠️ YES |
| `slot_recommendation` | ✅ success | RandomForest | **5** | 0.000 | 0.000 | 1.000 | ⚠️ YES |
| `vendor_ranking` | ✅ success | RandomForest | **4** | 0.000 | 0.000 | 1.000 | ⚠️ YES |
| `fraud_detection` | ✅ success | RandomForest | **27** | — | — | Accuracy: 0.800 | ⚠️ YES |

---

## Per-Model Detail

### 1. ETA Prediction (`eta_prediction`)

- **Version:** `eta_prediction_v2`
- **Rows trained:** 26 _(threshold: ≥ 200)_
- **Features:** 7 (`vendor_id`, `queue_length`, `slot_occupancy`, `item_count`, `time_of_day`, `weekday`, `rush_hour`)

| Model | MAE | RMSE | R² |
|---|---|---|---|
| **RandomForest** ✅ winner | 0.000 | 0.000 | 1.000 |
| XGBoost | 0.083 | 0.079 | 1.000 |
| LightGBM | 0.013 | 0.000 | 1.000 |

> [!WARNING]
> **LOW CONFIDENCE — treat heuristic as primary.**
> Only 26 training rows against a 200-row minimum. RMSE=0 and R²=1.0 indicate
> near-perfect memorisation of a tiny dataset. The model will not generalise to new
> vendor/slot/queue combinations. The `predict_with_fallback` bridge correctly falls
> back to the heuristic for vendors with < 30 historical orders; that gate will fire
> for almost every vendor at this data volume.

---

### 2. Demand Forecast (`demand_forecast`)

- **Version:** `demand_forecast_v2`
- **Rows trained:** 28 _(threshold: ≥ 200)_
- **Features:** 5 (`hour`, `weekday`, `day_of_month`, `month`, `rush_hour`)

| Model | MAE | RMSE | R² |
|---|---|---|---|
| **XGBoost** ✅ winner | 0.000 | 0.000 | 1.000 |
| RandomForest | 0.039 | 0.089 | 1.000 |

> [!WARNING]
> **LOW CONFIDENCE — treat heuristic as primary.**
> Only 28 hourly-bucket rows (aggregated across all vendors over 90 days). The model
> has memorised the handful of seen hour/weekday combinations. The 90-day history gate
> in `demand_planner.py` will prevent model calls for vendors without sufficient
> history; given current data, that gate will block model usage for all vendors.

---

### 3. Slot Recommendation (`slot_recommendation`)

- **Version:** `slot_recommendation_v2`
- **Rows trained:** 5 _(threshold: ≥ 20 slots)_
- **Features:** 6 (`occupancy`, `hour`, `weekday`, `rush_hour`, `avg_completion_minutes`, `max_capacity`)

| Model | MAE | RMSE | R² |
|---|---|---|---|
| **RandomForest** ✅ winner (only candidate) | 0.000 | 0.000 | 1.000 |

> [!CAUTION]
> **LOW CONFIDENCE — treat heuristic as primary.**
> Only 5 slots in the database. With a single model candidate and 5 samples, the
> test-set evaluation has ≤ 1 sample. The RMSE=0 is meaningless. The safety rule
> (exclude slots at ≥ 90% occupancy) remains fully operational regardless of model
> confidence.

---

### 4. Vendor Ranking (`vendor_ranking`)

- **Version:** `vendor_ranking_v2`
- **Rows trained:** 4 _(threshold: ≥ 10 vendors)_
- **Features:** 6 (`completion_rate`, `avg_rating`, `repeat_customer_rate`, `cancellations`, `refunds`, `total_orders`)

| Model | MAE | RMSE | R² |
|---|---|---|---|
| **RandomForest** ✅ winner | 0.000 | 0.000 | 1.000 |
| XGBoost | 0.000 | 0.000 | 1.000 |

> [!CAUTION]
> **LOW CONFIDENCE — treat heuristic as primary.**
> Only 4 approved vendors in the database. Both models achieve perfect scores — a
> trivial result with 4 data points. At this scale the models are simply sorting 4
> vendors, not learning a generalisable ranking function. The heuristic weighted-score
> formula (completion speed × 0.30 + success rate × 0.25 + ...) is more trustworthy
> than a model trained on 4 rows. Express-pickup eligibility continues to be enforced
> as a hard rule independent of model output.

---

### 5. Fraud Detection (`fraud_detection`)

- **Version:** `fraud_detection_v2`
- **Rows trained:** 27 _(users evaluated)_
- **Algorithm:** RandomForest Classifier (class-weight balanced)
- **Features:** 6 (`total_orders_30d`, `cancelled_orders_30d`, `cancel_rate`, `avg_amount`, `has_device_token`, `fraud_flagged_count`)

| Metric | Value |
|---|---|
| **Accuracy** | 0.800 |
| Precision | see raw JSON |
| Recall | see raw JSON |
| F1 | see raw JSON |

> [!WARNING]
> **LOW CONFIDENCE — treat heuristic as primary.**
> Only 27 user rows trained, with a dummy positive forced into the target vector
> (label `y[0]=1.0`) to enable binary classification (all real users are non-fraudulent
> at this stage). The 0.80 accuracy reflects the model correctly predicting "not fraud"
> for the majority class — this is not meaningful signal. Real fraud detection requires
> genuine positive labels at scale.

---

## Overfitting Diagnostic

All regression models report RMSE = 0.000 and R² = 1.000. This is **not** a good result — it is the expected output when:

- The test set is 20% of a tiny dataset (e.g. 20% × 5 rows = 1 test sample)
- The model has enough capacity to perfectly memorise every training point

The models are technically valid scikit-learn/XGBoost artifacts stored in the registry and loadable via `ModelRegistry.load()`. The `predict_with_fallback` bridges will attempt to use them when called. However, the data-volume gates defined in each planner are the correct first line of defence:

| Planner | Gate | Effect at current data volume |
|---|---|---|
| `eta_engine.py` | `>= 30 orders per vendor` | **Blocks all model calls** (0 vendors qualify) |
| `demand_planner.py` | `>= 90 days of order history` | **Blocks all model calls** (no vendor has 90-day history) |
| `vendor_ranker.py` | None — always calls bridge | Bridge calls model; model scores 4 vendors; heuristic is safer |
| `slot_planner.py` | None — always calls bridge | Bridge calls model; >90% safety rule enforced post-call |
| Fraud | Not wired through bridge yet | Heuristic path in `MLPredictionService.detect_fraud` |

---

## Recommended Actions Before Model Confidence Improves

1. **Accumulate data**: ETA and demand models need ≥ 200 completed orders with `actual_completion_minutes` populated. At current velocity, re-evaluate after 2–3 months of live traffic.
2. **Populate `actual_completion_minutes`**: Many orders appear to use `eta_minutes` as a fallback (see `extract_eta_training_data`). Ensure order completion timestamps are being recorded.
3. **Vendor ranking**: Onboard ≥ 10 approved vendors before trusting the ranking model over the heuristic.
4. **Slot recommendation**: Add more time-slot variety (more slots per vendor, more vendors) before model scores are meaningful.
5. **Fraud detection**: Real fraud labels (from manual review or payment chargebacks) are required before the model can be trusted.
6. **Re-run training**: After data accumulates, re-run `run_training_and_capture.py` and regenerate this document. A healthy model should show RMSE significantly above 0 (it has variance to explain) and R² in the range 0.6–0.95.

---

*Generated by `run_training_and_capture.py`. Raw training output: `docs/training_raw_results.json`*
