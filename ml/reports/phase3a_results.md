# Phase 3A: Trade Quality Filter — Results

**Date:** 2025-01-10  
**Baseline:** 15m SuperTrend with 1m+15m K=2 confirmation (PF 1.16, 448 trades, max DD -6040 pips)

---

## Executive Summary

**FAILED** to meet Phase 3A acceptance gates. ML trade quality filter shows no discriminative power:

- **Test AUC:** 0.599 (Logistic), 0.516 (LightGBM) — both barely above random (0.5)
- **Predicted probabilities:** 0.26–0.47 (all below 0.5 despite 40% actual win rate)
- **Feature signals:** Weak (highest MI: 0.015 for `sec_asia_range_atr`)
- **LightGBM overfitting:** Val AUC 0.589 → Test AUC 0.516 (100 "no splits" warnings)
- **Threshold sweep:** Zero trades retained at P≥0.50 (model predicts all trades as low probability)

**Recommendation:** Accept baseline 15m K=2 strategy without ML filter. Current features lack predictive signal; baseline already near-optimal.

---

## Models Trained

### Logistic Regression (Baseline)
- **Val AUC:** 0.583
- **Test AUC:** 0.599
- **Confusion Matrix (Test):** All 100 trades predicted as negative class (precision/recall = 0)
- **Convergence:** Failed after 500 iterations (lbfgs, expected with weak features)
- **Features:** 31 total (20 primary + 11 secondary, includes 5 constant session flags)

### LightGBM (Tree-Based Upgrade)
- **Val AUC:** 0.589
- **Test AUC:** 0.516 (WORSE than Logistic, severe overfitting)
- **Training warnings:** 100 "No further splits with positive gain" → memorized validation set
- **Top features by gain:**
  1. `dow` (296.4) — day of week (likely spurious temporal pattern)
  2. `hour` (119.7) — entry hour
  3. `up_count` (85.5) — multi-timeframe trend consensus
  4. `open` (70.4) — bar open price
  5. `close` (67.5) — bar close price

**Diagnosis:** LightGBM fit noise in small dataset (462 train samples), captured spurious day-of-week patterns, failed to generalize.

---

## Probability Distribution Analysis

Model predicts all test trades as <50% win probability (severely underconfident):

```
Test set: 100 trades, 40 wins (40.0% actual)

Predicted probabilities:
  Min:  0.2636
  Max:  0.4657
  Mean: 0.3536 (vs 40% actual)
  Std:  0.0449

Threshold coverage:
  % above 0.50: 0.0%
  % above 0.40: 15.0%
  % above 0.30: 94.0%

Deciles:
  10th: 0.3344
  25th: 0.3384
  50th: 0.3422
  75th: 0.3468
  90th: 0.4467
  95th: 0.4509
  99th: 0.4590
```

**Issue:** Narrow prediction range (0.26–0.47) with mean 0.35 despite 40% actual win rate → severe underfitting. Features cannot discriminate winners from losers.

---

## Threshold Sweep Results

All thresholds P≥0.50 retain **zero trades** (sweep range 0.50–0.80, step 0.02).

**Test baseline PF:** 1.33 (100 trades)  
**Filtered PF at P≥0.50:** N/A (0 trades retained)

Cannot achieve Phase 3A gate: PF improvement ≥+0.10 (1.16 → 1.26).

---

## Feature Signal Strength (Post-Bugfix)

After fixing session labeling bug (all trades mislabeled as midnight Asian session), true feature signals emerged:

| Feature | Mutual Info | Notes |
|---------|-------------|-------|
| `sec_asia_range_atr` | 0.015 | Asian session range (ATR-normalized) — highest signal |
| `sec_entry_below_asia_low` | 0.008 | Breakout below Asian low |
| `tf_30m_up` | 0.0053 | 30m trend direction |
| `hour` | 0.0034 | Entry hour (13–15 UTC overlap session) |
| `up_count` | 0.000 | Multi-TF consensus (MI=0 despite quantile PF varies: low 1.47 vs high 1.16) |

**6 constant session flags removed:** `sec_is_asia`, `sec_is_london`, `sec_is_overlap`, `sec_is_ny_late`, `sec_is_off`, `sec_session` (all zero variance — all trades enter 13:00–15:59 UTC overlap session).

**Observation:** Features show weak linear signals (MI <0.02). LightGBM tried to capture non-linear patterns (e.g., `up_count` threshold effect) but overfitted instead.

---

## Data Quality Issues Resolved

1. **Session labeling bug** (CRITICAL):
   - **Issue:** All 661 trades mislabeled as `hour=0`, `sec_is_asia=1` (midnight Asian session)
   - **Root cause:** 1-minute OHLC resampling created daily bars at 00:00 instead of intraday bars; script used bar timestamp for hour/session labels
   - **Fix:** Changed `extract_features.py` to use trade entry timestamp (`ts`) instead of bar timestamp (`bar_ts`) for hour/dow/session features
   - **Verification:** All trades correctly labeled as `hour=13-15`, `sec_is_overlap=1`

2. **NaN handling:**
   - **Issue:** Median imputation left NaN in all-NaN columns (ATR/EMA features with missing indicator data)
   - **Fix:** Chained fillna: `fillna(median()).fillna(0)`

---

## Phase 3A Gate Evaluation

| Gate | Target | Result | Pass/Fail |
|------|--------|--------|-----------|
| Test AUC | ≥0.65 (moderate discrimination) | 0.599 (LR), 0.516 (GBM) | ❌ FAIL |
| PF improvement | +0.10 vs baseline (1.16 → 1.26) | Cannot measure (0 trades at P≥0.50) | ❌ FAIL |
| Trade retention | ≥60% (397+ trades) | 0% at P≥0.50 | ❌ FAIL |
| Outlier retention | ≥85% of top 10% trades | 0% at P≥0.50 | ❌ FAIL |

**Overall: REJECT** — Model lacks predictive power. ML filter adds no value to baseline strategy.

---

## Root Cause Analysis

1. **Weak feature signals:** Highest true MI = 0.015 (Asian range) — insufficient for reliable classification
2. **Homogeneous strategy:** All 661 trades from same 15m K=2 setup → low variance in trade characteristics
3. **Small sample size:** 462 train trades insufficient for tree models (LightGBM overfits)
4. **Class imbalance calibration:** Model predicts mean 0.35 probability vs 40% actual → underconfident (could improve with calibration, but AUC already shows weak discrimination)
5. **Missing engineered features:** Current features lack interaction terms, regime indicators, volatility-adjusted metrics that might capture trade quality patterns

---

## Recommendations

### Short-Term: Accept Baseline Without ML
- **Baseline 15m K=2 already near-optimal** (PF 1.16 vs 1.07 K=1, 1.16 K=2, 1.13 K=3+ — K=2 is peak)
- ML filter provides no benefit with current feature set
- **Action:** Document Phase 3A failure in `plan.md`, proceed to backtesting/live deployment of baseline

### Medium-Term: Feature Engineering (If Pursuing ML)
If revisiting ML in future with expanded strategy (more setups, longer history):

1. **Engineered features:**
   - `up_count` binned (low 1-2, med 3, high 4-5) to capture non-linear threshold effect
   - `hour` buckets (overlap=13-16, NY=16-20, quiet=other)
   - Distance to Asian high/low (ATR-normalized)
   - Recent volatility regime (5-day ATR percentile)
   - Time since last big move (gap >1.5*ATR)

2. **Regime features:**
   - Daily trend classifier (Phase 3B, but requires longer history)
   - Intraday range expansion (current range vs daily ATR)

3. **External data:**
   - High-impact news schedule (avoid 30m before/after)
   - Market breadth indicators (if multi-asset expansion planned)

### Long-Term: Expand Data Diversity
- **Current limitation:** Single 15m setup with 661 trades → homogeneous feature distribution
- **Solution:** Collect trades from multiple setups (5m, 30m, 1h), different parameter sweeps → 2000+ trades with diverse characteristics
- Re-train models on expanded dataset with engineered features

---

## Files Generated

- `ml/models/trade_quality_lr.pkl` — Logistic Regression (Test AUC 0.599)
- `ml/models/trade_quality_gbm.pkl` — LightGBM (Test AUC 0.516, overfitted)
- `ml/models/metadata/*.json` — Model metadata (metrics, confusion matrices, feature lists)
- `ml/reports/feature_importance_gbm.csv` — LightGBM feature gain rankings
- `results/ml/threshold_sweep_results.csv` — Empty sweep (0 trades at P≥0.50)
- `data/features/trades_features.parquet` — 661 trades × 32 features (corrected session labels)
- `ml/FEATURES_GUIDE.md` — Plain English feature documentation

---

## Next Steps

1. **Update `plan.md`:** Mark Phase 3A as FAILED, document lessons learned
2. **Backtest baseline:** Test 15m K=2 on out-of-sample data (2023+ if available)
3. **Live deployment:** Paper trade baseline 15m K=2 for 1-2 months to validate in production
4. **Archive ML code:** Keep `scripts/ml/` for future revisit if strategy expands to multiple setups

**ML enhancement postponed until:**
- Strategy diversification (multiple timeframes/setups → 2000+ trades)
- Feature engineering iteration (binned up_count, regime indicators)
- Longer backtest history (3+ years for regime-based features)
