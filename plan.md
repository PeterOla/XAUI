# XAUI Project Plan — ML Roadmap Focus

Goal: Boost profit factor (PF), Sharpe, and drawdown stability by adding Machine Learning layers on top of the established 15m SuperTrend baseline (up_buy_only).

---
## Baseline (Reference State)
Status: COMPLETE
- Strategy: 15m SuperTrend, trade Long only on 15m Up-trend days.
- Enhancements baked in: Multi-timeframe trend files, K-of-N confirmation, Up-count aggregation, performance summaries.
- Chosen filter setting going forward: 1m+15m with K=2 (better PF & DD vs K=1).

Artifacts (reference):
- `results/trends/combo_15m_1m_k2of2/trades_simple_up_buy_only.csv`
- `results/trends/aggregate_upcount_summary.csv`

---
## Phase 3A — Trade Quality (Meta-Label) Filter

**Status: FAILED — Model lacks predictive power (Test AUC 0.599 Logistic, 0.516 LightGBM)**

**Date Completed:** 2025-11-10  
**Results:** `ml/reports/phase3a_results.md`

Purpose: Predict if each candidate trade is "high quality" before taking it; discard weak ones.

### Key Findings
- **Root cause:** Homogeneous trade population (all 661 trades from same 15m K=2 setup), weak feature signals (highest MI: 0.015), small sample size (462 train)
- **Model performance:** All predictions <0.50 probability despite 40% actual win rate (severe underfitting)
- **LightGBM overfitting:** Val AUC 0.589 → Test AUC 0.516, 100 "no splits" warnings
- **Threshold sweep:** Zero trades retained at P≥0.50 (no useful operating point)
- **Acceptance gates:** FAILED all criteria (PF +0.10, 60% retention, 85% outlier retention)

### Lessons Learned
1. Current features (price action, trend indicators, session context) insufficient to discriminate trade quality
2. Need diverse trade population (multiple setups, timeframes, parameters → 2000+ trades)
3. Need engineered features (non-linear interactions, regime indicators, threshold effects)
4. Adding more indicators (MACD, RSI) won't help without addressing fundamental data constraints

### Recommendation
**Accept 15m K=2 baseline (PF 1.16) without ML filter.** Revisit ML after expanding strategy diversity.

Checklist (Completed)
- [x] Freeze data snapshot & define time splits (Train 70% | Val 15% | Test 15%).
- [x] Extract baseline trades (15m K=2 combo) → 661 trades from combined results.
- [x] Implement `scripts/ml/extract_features.py`:
- [x] Implement `scripts/ml/extract_features.py`:
  - [x] Load trades + underlying OHLC data.
  - [x] Generate features per trade:
    - [x] Candle body % = |Close-Open| / (High-Low)
    - [x] Upper / lower wick %
    - [x] ATR(14) at entry (15m bars)
    - [x] Distance to EMA200 (pips & pct of ATR)
    - [x] Multi-timeframe Up-count (1m,5m,15m,30m,1h)
    - [x] Hour-of-day
    - [x] Day-of-week
    - [x] Asian session range & breakout indicators
    - [x] London open range
    - [x] Session flags
  - [x] Export parquet: `data/features/trades_features.parquet` (661 rows × 32 features)
- [x] Label definition v1: High-quality = pips > 0 (40% win rate).
- [x] Time-based splits (70/15/15 no shuffle) & leakage check.
- [x] Train baseline Logistic Regression → `ml/models/trade_quality_lr.pkl` (Test AUC 0.599).
- [x] Evaluate: ROC-AUC 0.599, Precision/Recall 0 (all negative predictions).
- [x] Train LightGBM upgrade → `ml/models/trade_quality_gbm.pkl` (Test AUC 0.516, overfitted).
- [x] Probability threshold sweep (0.50→0.80 step 0.02) → Zero trades retained (all predictions <0.5).
- [x] Feature evaluation: Weak signals (MI <0.02), constant session flags removed.
- [x] Fixed critical session labeling bug (midnight timestamps instead of actual entry times).
- [-] ~~Pick threshold meeting gates~~ — Not applicable (no useful threshold found).
- [-] ~~Integrate gating into `base_strategy.py`~~ — Deferred (gates not met).
- [x] Report: `ml/reports/phase3a_results.md` (full analysis, probability distribution, overfitting diagnosis).

Checklist (Not Attempted - Gates Failed)
- [ ] Alternate label experiment: pips ≥ median win (record comparison).
- [ ] Previous 5 trades mean pips feature
- [ ] Previous 5 trades pips stdev feature
- [ ] Win/loss streak length (signed) feature
- [ ] Initial stop distance (pips) feature
- [ ] Intraday range / 20-day median range feature

Acceptance Gates (FAILED)
- ❌ PF + ≥0.10 absolute vs baseline — Cannot measure (0 trades at P≥0.50).
- ❌ Retain ≥60% of baseline trade count — 0% retained at P≥0.50.
- ❌ Retain ≥85% of top-decile winners — 0% retained at P≥0.50.

Artifacts Created
- `data/features/trades_features.parquet` — 661 trades × 32 features
- `data/features/splits/train_indices.csv` — 462 trades (70%)
- `data/features/splits/val_indices.csv` — 99 trades (15%)
- `data/features/splits/test_indices.csv` — 100 trades (15%)
- `ml/models/trade_quality_lr.pkl` — Logistic Regression model
- `ml/models/trade_quality_gbm.pkl` — LightGBM model (overfitted)
- `ml/models/metadata/*.json` — Model metadata (metrics, confusion matrices)
- `ml/reports/feature_importance_gbm.csv` — Feature gain rankings
- `ml/reports/phase3a_results.md` — Comprehensive failure analysis
- `results/ml/features_univariate_summary.md` — Mutual information analysis
- `results/ml/features_quantile_pf.csv` — 5-bin PF by feature
- `results/ml/threshold_sweep_results.csv` — Empty sweep results

---
## Phase 3A-R — ML Enhancement Roadmap (Revised)

**Purpose:** Address root causes of Phase 3A failure before attempting ML again.

**Prerequisites:** Complete at least one item from Data Expansion AND Feature Engineering sections.

### 1. Data Expansion (Critical Priority)

**Goal:** Increase trade diversity from 661 homogeneous trades → 2000+ diverse samples

Checklist
- [ ] **Multi-timeframe expansion:**
  - [ ] Run 5m SuperTrend backtest (same K=2 logic) → target 300+ trades
  - [ ] Run 30m SuperTrend backtest → target 200+ trades
  - [ ] Run 1h SuperTrend backtest → target 150+ trades
  - [ ] Combine all timeframes into unified dataset with `timeframe` feature
- [ ] **Parameter sweep expansion:**
  - [ ] Test ST period variations: 8, 10, 12 (currently 10) × 3 timeframes → 9 combinations
  - [ ] Test ST multiplier variations: 3.0, 3.3, 3.6, 4.0 (currently 3.6) × 3 timeframes → 12 combinations
  - [ ] Collect all "reasonable PF" variants (PF >1.0) into dataset
- [ ] **Strategy diversification (optional, long-term):**
  - [ ] Add EMA crossover strategy (50/200 cross)
  - [ ] Add breakout strategy (Asian range breakout)
  - [ ] Add mean reversion strategy (Bollinger Band bounces)
- [ ] **Validation:** Target ≥2000 trades with variance in entry conditions, timeframes, market regimes

### 2. Feature Engineering (High Priority)

**Goal:** Capture non-linear patterns and threshold effects revealed in Phase 3A analysis

Checklist
- [ ] **Regime-based features:**
  - [ ] `up_count_regime`: Binned (low=1-2, med=3, high=4-5) — Phase 3A found low consensus PF 1.47 vs high 1.16
  - [ ] `hour_bucket`: Categorical (overlap=13-16, ny=16-20, quiet=other)
  - [ ] `volatility_regime`: Daily ATR percentile (rolling 20-day)
  - [ ] `trend_strength`: EMA200 slope / ATR (normalized momentum)
- [ ] **Distance/breakout features (ATR-normalized):**
  - [ ] `dist_to_asian_high_atr`: (close - asian_high) / atr14
  - [ ] `dist_to_asian_low_atr`: (asian_low - close) / atr14
  - [ ] `dist_to_london_open_atr`: Distance from London open price
  - [ ] `range_expansion_pct`: Current range / 20-day median range
- [ ] **Interaction features:**
  - [ ] `up_count_x_hour`: Capture "low consensus in overlap session" pattern
  - [ ] `atr_x_range_expansion`: Volatility context (expanding vs contracting)
  - [ ] `ema_dist_x_trend_strength`: Strong trend with close alignment
- [ ] **Momentum indicators (test for incremental value):**
  - [ ] RSI(14) at entry (overbought/oversold context)
  - [ ] MACD histogram at entry (momentum divergence)
  - [ ] Note: Only add if MI > 0.02 or improves model AUC >0.03
- [ ] **Sequence features:**
  - [ ] Previous 3 trades mean pips (recent performance context)
  - [ ] Consecutive wins/losses (streak length, signed)
  - [ ] Bars since last trade (trade frequency context)
- [ ] **Validation:** Re-run `evaluate_features.py` on expanded dataset; verify MI scores >0.02 for engineered features

### 3. Model Improvements

**Goal:** Address overfitting and calibration issues

Checklist
- [ ] **Regularization & hyperparameter tuning:**
  - [ ] LightGBM: Reduce max_depth (try 3, 4 vs default 6), increase min_child_samples (20, 50)
  - [ ] Add early stopping (20 rounds no improvement on validation)
  - [ ] L2 regularization (lambda_l2 = 1.0, 5.0)
- [ ] **Probability calibration:**
  - [ ] Apply isotonic or Platt calibration to Logistic Regression (fix underconfident predictions)
  - [ ] Check if calibrated probabilities span 0.3-0.7 range (vs current 0.26-0.47)
- [ ] **Alternative models (if LightGBM continues overfitting):**
  - [ ] Random Forest with max_depth=5, min_samples_leaf=20 (more conservative)
  - [ ] XGBoost with stricter regularization
  - [ ] Ensemble: Average Logistic + calibrated tree model
- [ ] **Cross-validation:** 5-fold time-series CV instead of single 70/15/15 split (more robust validation)

### 4. Experimental: Daily Regime Pre-Filter (Phase 3B Simplified)

**Goal:** Filter out entire bad days before individual trade scoring

Checklist
- [ ] **Aggregate daily features:**
  - [ ] EMA200 distance z-score (mean across 5 timeframes)
  - [ ] Up-count ratio: # timeframes up / total (consensus measure)
  - [ ] Daily volatility: First-hour ATR vs 20-day median
  - [ ] Prior 3-day strategy pips (momentum)
- [ ] **Label:** Good day = daily total pips > 0 (binary classification)
- [ ] **Model:** Logistic Regression or simple decision tree (interpretable)
- [ ] **Integration:** Skip all trades on days predicted as "bad" (P(good) <0.4)
- [ ] **Validation:** Check if filtering improves PF +0.05 and reduces max DD >5%

### 5. Alternative: Rule-Based Filter (Non-ML Fallback)

**Goal:** Simple heuristics from Phase 3A insights

Checklist
- [ ] **Rule 1:** Skip trades with `up_count ≥ 4` (high consensus = lower PF per quantile analysis)
- [ ] **Rule 2:** Only take trades during `hour 13-16` (overlap session peak)
- [ ] **Rule 3:** Require `sec_asia_range_atr < 0.8` (low volatility setup)
- [ ] **Rule 4:** Skip if `ema_dist_atr > 2.0` (too extended from trend)
- [ ] **Backtest:** Combine rules, measure PF improvement vs baseline
- [ ] **Compare:** Rule-based vs ML models (if rules outperform, accept simpler solution)

### Acceptance Gates (Revised for Phase 3A-R)

Must meet ONE of the following:

**Option A: ML Model Success**
- Test AUC ≥0.65 (moderate discrimination)
- PF improvement ≥+0.10 vs baseline (1.16 → 1.26)
- Retain ≥60% of baseline trade count
- Retain ≥85% of top-decile winners
- Predictions span 0.3-0.7 probability range (no severe calibration issues)

**Option B: Rule-Based Success**
- PF improvement ≥+0.08 vs baseline (1.16 → 1.26)
- Retain ≥50% of baseline trade count (simpler rules = more aggressive filtering acceptable)
- Max DD reduction ≥5%

**Option C: Accept Baseline**
- If neither A nor B achieved after Data Expansion + Feature Engineering iteration
- Document that 15m K=2 baseline is near-optimal, proceed to live trading

---
## Phase 3A-R — ML Enhancement Roadmap (Revised)

**Purpose:** Address root causes of Phase 3A failure before attempting ML again.

**Prerequisites:** Complete at least one item from Data Expansion AND Feature Engineering sections.

### 1. Data Expansion (Critical Priority)

**Goal:** Increase trade diversity from 661 homogeneous trades → 2000+ diverse samples

Checklist
- [ ] **Multi-timeframe expansion:**
  - [ ] Run 5m SuperTrend backtest (same K=2 logic) → target 300+ trades
  - [ ] Run 30m SuperTrend backtest → target 200+ trades
  - [ ] Run 1h SuperTrend backtest → target 150+ trades
  - [ ] Combine all timeframes into unified dataset with `timeframe` feature
- [ ] **Parameter sweep expansion:**
  - [ ] Test ST period variations: 8, 10, 12 (currently 10) × 3 timeframes → 9 combinations
  - [ ] Test ST multiplier variations: 3.0, 3.3, 3.6, 4.0 (currently 3.6) × 3 timeframes → 12 combinations
  - [ ] Collect all "reasonable PF" variants (PF >1.0) into dataset
- [ ] **Strategy diversification (optional, long-term):**
  - [ ] Add EMA crossover strategy (50/200 cross)
  - [ ] Add breakout strategy (Asian range breakout)
  - [ ] Add mean reversion strategy (Bollinger Band bounces)
- [ ] **Validation:** Target ≥2000 trades with variance in entry conditions, timeframes, market regimes

### 2. Feature Engineering (High Priority)

**Goal:** Capture non-linear patterns and threshold effects revealed in Phase 3A analysis

Checklist

---
## Phase 3B — Daily Regime Scoring

**Status: DEFERRED** — Awaiting Phase 3A-R completion (requires expanded dataset)

Purpose: Rate each day (Strong / Neutral / Avoid) pre-market. Skip or downsize weak days.

Checklist
- [ ] Build daily feature set script `scripts/build_daily_regime_features.py`:
  - EMA distance z-scores per TF (1m,5m,15m,30m,1h).
  - EMA slope normalized by ATR.
  - Volatility compression: intraday range / 20-day median range.
  - Up-count ratio (# Up / total TFs).
  - Prior 3-day cumulative strategy pips.
  - Rolling equity slope (regression over last 50 trades’ cumulative pips).
- [ ] Labeling:
  - Strong: day total pips > 75th percentile.
  - Neutral: 25th–75th percentile.
  - Avoid: <25th percentile or negative.
- [ ] Train classifier (LightGBM multi-class) → `ml/models/day_regime.pkl`.
- [ ] Derive regime score = P(Strong).
- [ ] Threshold experiments for skipping Avoid days; document PF, DD, trade count impact.
- [ ] Integrate gating:
  - Flags: `--regime-filter ml/models/day_regime.pkl` & `--regime-threshold <t>`.
  - Size tiers (optional): Strong=1.0, Neutral=0.7, Avoid=0.
- [ ] Report: `ml/reports/daily_regime_metrics_<date>.md` (confusion matrix, PF/DD table per regime).

Acceptance Gates
- Max DD reduction ≥10% vs ungated baseline.
- PF neutral or improved.
- Retain ≥50% of trades.

---
## Phase 3C — Quantile / Distribution-Based Sizing

**Status: DEFERRED** — Awaiting Phase 3A-R completion (requires expanded dataset)

Purpose: Predict downside (risk) and upside (reward) ranges; size trades where reward outweighs risk.

Checklist
- [ ] Extend feature set (add time since last signal, prior day range, ATR trend slope).
- [ ] Train quantile model (LightGBM quantile or NGBoost): predict Q20, Q50, Q80 pips.
- [ ] Compute score = Q50 / |Q20| per trade.
- [ ] Size map: score <0.8 → 0.5x; 0.8–1.2 → 1.0x; >1.2 → 1.3x (cap).
- [ ] Daily VAR check: sum(size * |Q20|) ≤ predefined limit.
- [ ] Drawdown safety: disable >1.0x sizing if current equity DD > threshold.
- [ ] Integrate sizing flag: `--quantile-model ml/models/quantile_sizing.pkl --sizing-enabled`.
- [ ] Simulated curve vs baseline; compute Sharpe, max DD, worst trade impact.
- [ ] Report: `ml/reports/quantile_sizing_metrics_<date>.md`.

Acceptance Gates
- Sharpe ≥ +15% vs baseline.
- Max DD not worse.
- Worst trade magnitude not larger than baseline worst.

---
## Monitoring & Drift Control

Checklist
- [ ] Implement `scripts/monitor_ml.py`:
  - Weekly PF, Sharpe, retention %, regime distribution.
  - Drift signals: probability compression (std < threshold), retention collapse (<40%).
  - Auto-generate `ml/reports/drift_alert_<date>.md` on anomalies.
- [ ] Adaptive threshold logic (optional): recalibrate every 4 weeks if PF drop > set %.
- [ ] Fallback: disable ML layers automatically if drift alert persists 2 consecutive weeks.

---
## Versioning & Reproducibility

Checklist
- [ ] `ml/README.md` summarizing each model (features, date, metrics, threshold).
- [ ] Save `feature_schema_trade_quality.json`, `feature_schema_regime.json`.
- [ ] Include training parameters JSON per model.
- [ ] Store dataset slice hash (commit hash + date range).
- [ ] Maintain changelog inside `ml/README.md`.

---
## Risk Controls (Integration Points)

Checklist
- [ ] Max consecutive rejected trades watchdog (adjust threshold downward if triggered).
- [ ] Cooldown: pause new trades N bars after equity DD > X.
- [ ] Emergency bypass flag: `--disable-ml`.
- [ ] Logging: structured JSON per run capturing ML decisions.

---
## Current Status Table

| Component                | Status    | Notes |
|--------------------------|-----------|-------|
| Baseline 15m + K=2       | ✅ DONE   | PF 1.16, 448 trades, max DD -6040 pips |
| Feature Extraction (3A)  | ✅ DONE   | 661 trades × 32 features, session bug fixed |
| Trade Quality Models     | ❌ FAILED | Test AUC 0.599 (LR), 0.516 (GBM), no useful threshold |
| Phase 3A-R Roadmap       | 📋 PLANNED | Data expansion + feature engineering path defined |
| Regime Scoring (3B)      | ⏸️ DEFERRED | Awaiting 3A-R completion |
| Quantile Sizing (3C)     | ⏸️ DEFERRED | Awaiting 3A-R completion |
| Monitoring / Drift       | PENDING   | |
| Risk Controls            | PENDING   | |
| Versioning Artifacts     | PENDING   | |

---
## Execution Order (Recommended — Updated)

### Current Priority: Phase 3A-R
1. ✅ ~~Feature extraction script & dataset parquet~~ — COMPLETE (661 trades)
2. ✅ ~~Logistic regression baseline + threshold sweep~~ — COMPLETE (failed gates)
3. ✅ ~~LightGBM trade quality model~~ — COMPLETE (overfitted)
4. 📋 **NEXT: Data expansion** (multi-timeframe backtests OR parameter sweep)
5. 📋 **THEN: Feature engineering** (regime bins, interactions, distance features)
6. 📋 **THEN: Re-train models** with expanded dataset + engineered features
7. 📋 **THEN: Validate gates** (AUC ≥0.65, PF +0.10, retention targets)
8. 📋 **OPTIONAL: Rule-based filter** (if ML continues failing)

### Deferred Until Phase 3A-R Success
9. Daily regime feature build + classifier & gating (Phase 3B)
10. Quantile sizing model & simulation (Phase 3C)
11. Monitoring / drift script
12. Risk controls & adaptive thresholds
13. Versioning & README finalization

---
## Acceptance Gate Summary

| Layer          | PF Gain | Retention | DD Impact    | Outlier Retention | Sharpe Gain | Status |
|--------------- |-------- |---------- |------------- |------------------ |------------ |--------|
| Trade Quality (3A) | +0.10   | ≥60%      | ≤ -10% vs base | ≥85% top winners  | Secondary   | ❌ FAILED |
| Trade Quality (3A-R) | +0.10   | ≥60%      | Neutral | ≥85% top winners  | Secondary   | 📋 PLANNED |
| Regime Scoring (3B) | Neutral/+ | ≥50%    | ≥10% DD ↓    | ≥85% top winners  | Secondary   | ⏸️ DEFERRED |
| Quantile Sizing (3C)| N/A     | N/A       | Not worse    | N/A               | +15%        | ⏸️ DEFERRED |

---
## Artifacts (Created & Planned)

### Completed (Phase 3A)
- ✅ `data/features/trades_features.parquet` — 661 trades × 32 features
- ✅ `data/features/splits/*.csv` — Train/val/test indices (70/15/15)
- ✅ `ml/models/trade_quality_lr.pkl` — Logistic Regression (AUC 0.599)
- ✅ `ml/models/trade_quality_gbm.pkl` — LightGBM (AUC 0.516, overfitted)
- ✅ `ml/models/metadata/*.json` — Model metrics, confusion matrices
- ✅ `ml/reports/feature_importance_gbm.csv` — Feature gain rankings
- ✅ `ml/reports/phase3a_results.md` — Comprehensive failure analysis
- ✅ `results/ml/features_univariate_summary.md` — Mutual information analysis
- ✅ `results/ml/features_quantile_pf.csv` — 5-bin PF by feature
- ✅ `results/ml/threshold_sweep_results.csv` — Empty sweep results

### Planned (Phase 3A-R)
- 📋 `data/features/trades_features_expanded.parquet` — 2000+ trades (multi-TF/parameters)
- 📋 `ml/models/trade_quality_v2_*.pkl` — Re-trained models with expanded data
- 📋 `ml/reports/phase3a_r_results.md` — Revised model evaluation
- 📋 `ml/reports/feature_engineering_impact.md` — Before/after MI comparison
- 📋 `ml/reports/rule_based_filter_comparison.md` — ML vs heuristics

### Planned (Phase 3B/3C - Deferred)
- ⏸️ `ml/models/day_regime.pkl`
- ⏸️ `ml/models/quantile_sizing.pkl`
- ⏸️ `ml/reports/daily_regime_metrics_<date>.md`
- ⏸️ `ml/reports/quantile_sizing_metrics_<date>.md`
- ⏸️ `ml/reports/drift_alert_<date>.md`
- ⏸️ `ml/README.md`

---
## Notes

### Key Learnings from Phase 3A
- **Homogeneous trade population** (all from same 15m K=2 setup) severely limits ML effectiveness
- **Small sample size** (462 train trades) leads to LightGBM overfitting (Val 0.589 → Test 0.516)
- **Weak feature signals** (highest MI: 0.015) insufficient for reliable classification
- **Session labeling bug** caught: 1-minute resampling created midnight bars instead of intraday bars
- **Constant features** (6 session flags with zero variance) showed spurious MI scores, removed
- **Non-linear patterns** exist (e.g., up_count low consensus PF 1.47 vs high 1.16) but require:
  - Larger dataset to learn reliably
  - Engineered features (binning, interactions) to capture explicitly
- **Calibration issues**: Model predicted 0.26-0.47 range despite 40% actual win rate

### Technical Guidelines (Unchanged)
- All splits strictly time-forward; never shuffle.
- No feature may use future info relative to trade entry or day start.
- Start simple (Logistic) for interpretability; escalate once gains verified.
- Keep ML off by default until gates passed; enable with explicit flags.
- Regularly archive model + schema + metrics for reproducibility.

### Decision Point
After Phase 3A-R attempt (data expansion + feature engineering):
- **If gates pass:** Continue to Phase 3B/3C
- **If gates fail again:** Accept 15m K=2 baseline as near-optimal, proceed to live trading
- **Rule-based alternative:** If simple heuristics outperform ML, adopt those instead

