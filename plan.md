# XAUI Trading Strategy - Development Plan# XAUI Project Plan — ML Roadmap Focus



## Project OverviewGoal: Boost profit factor (PF), Sharpe, and drawdown stability by adding Machine Learning layers on top of the established 15m SuperTrend baseline (up_buy_only).

SuperTrend-based XAUUSD (Gold) trading strategy with news sentiment filtering and ML enhancements.

---

---## Baseline (Reference State)

Status: COMPLETE

## ✅ COMPLETED PHASES- Strategy: 15m SuperTrend, trade Long only on 15m Up-trend days.

- Enhancements baked in: Multi-timeframe trend files, K-of-N confirmation, Up-count aggregation, performance summaries.

### Phase 1: Base Strategy Development ✅- Chosen filter setting going forward: 1m+15m with K=2 (better PF & DD vs K=1).

**Status:** Complete  

**Timeframe:** Initial development  Artifacts (reference):

- `results/trends/combo_15m_1m_k2of2/trades_simple_up_buy_only.csv`

**Achievements:**- `results/trends/aggregate_upcount_summary.csv`

- Implemented 15m SuperTrend (10/3.6/520) on 1-minute bars

- Entry pattern: Flip → Alternating candle → Entry confirmation---

- Max SL distance cap: 520 pips## Phase 3A — Trade Quality (Meta-Label) Filter [ATTEMPT 1-5 FAILED]

- Entry hours filter: 13-16 UTC (NY overlap)

- EMA200 daily trend filter**Status: COMPREHENSIVELY FAILED — All approaches unable to achieve Test AUC >0.55**

- Interactive plotting with Plotly

- Comprehensive performance metrics**Final Attempt Date:** 2025-11-11  

**Results:** Multiple iterations documented below

**Baseline Performance:**

- Full dataset: 2,490 trades, PF 1.13Purpose: Predict if each candidate trade is "high quality" before taking it; discard weak ones.

- Test set (Jan 2024+): 374 trades, PF 1.110, WR 37.97%, 14.94 avg pips

### Linear History of Attempts

---

#### Attempt 1: Baseline ML (FAILED - 2025-11-10)

### Phase 2: Data Quality & Infrastructure ✅**Dataset:** 661 trades from 15m K=2 up_buy_only  

**Status:** Complete**Features:** 32 basic features (price action, ATR, EMA distance, session flags)  

**Result:** Test AUC 0.599 (LR), 0.516 (GBM)  

**Achievements:****Root Cause:** Homogeneous trade population, weak signals (MI <0.015), small sample (462 train)

- GDELT news API integration

- FinBERT sentiment analysis (ProsusAI/finbert)#### Attempt 2: Data Expansion to 1,269 Trades (FAILED - 2025-11-10)

- Context-aware gold sentiment mapping**Dataset:** Expanded to full 1799-day up-trend period  

- Train/val/test splits (70/15/15)**Features:** Same 32 features  

- Deployment gates framework**Result:** Test AUC 0.494 (LR), 0.506 (GBM) - WORSE than Attempt 1  

- Look-ahead bias detection and correction**Root Cause:** More data but still homogeneous (all long-only), no new signal sources



**Key Fix:** Removed 3,266 future headlines (7.78%), cleaned to 38,700 headlines#### Attempt 3: Both-Sides Strategy (FAILED - 2025-11-10)

**Dataset:** 2,490 trades (1,269 longs PF 1.19 + 1,221 shorts PF 1.06 = combined PF 1.13)  

---**Features:** Same 32 + side encoding  

**Result:** Not trained - moved to enhanced features first  

### Phase 3A: News Sentiment Filter ✅**Learning:** Needed directional contrast AND better features

**Status:** Complete - TWO FILTERS VALIDATED  

**Completion Date:** November 12, 2025#### Attempt 4: Enhanced Technical Features (FAILED - 2025-11-10)

**Dataset:** Same 2,490 both-sides trades  

#### Journey:**Features:** 37 enhanced (RSI 14/30, MACD, Bollinger Bands, EMAs 20/50/200, momentum, ATR percentile, 5m multi-timeframe, session effects, interactions)  

1. **ML Attempts (5 iterations):** FAILED - AUC 0.442-0.502**Result:** Test AUC 0.472 (LR), 0.471 (GBM)  

2. **Manual News Database (111 events):** SUCCESS (10.5x advantage) but only 9 test trades ❌**Root Cause:** Even comprehensive technical indicators couldn't predict outcomes. Strongest signals: atr14_5m MI 0.016, is_overlap MI 0.013 (all weak)

3. **GDELT Generic Query:** FAILED - 478K headlines, 5.9% gold-relevant

4. **GDELT Refined Query:** SUCCESS - 42K headlines, 42.2% gold-relevant#### Attempt 5: Manual News Events Database (FAILED - 2025-11-11)

5. **Look-ahead Bias Discovery:** Fixed - removed 7.35% future headlines**Dataset:** 2,490 trades + manually coded 111 major events (2015-2025)  

6. **Final Validation:** TWO filters pass all gates! ✅- All Fed rate decisions, QE/tapering announcements

- CPI/NFP shocks, banking crises (SVB, Credit Suisse)

#### Filter 1: moderate_bearish (Contrarian Strategy)- Geopolitical events (Brexit, Trump elections, Russia-Ukraine, COVID crash)

```python**Features:** 44 total (37 technical + 7 news sentiment with time-decayed windows)  

headline_count >= 5 AND net_sentiment < -0.1**News Coverage:** 140 trades (5.6%) within 3 hours of major events  

```**Univariate Performance:** Trades near events showed 40.7% WR vs 35.9% baseline (+4.8pp), 89.35 avg pips vs 12.62 baseline (7.1x multiplier!)  

**Test Set Performance:****ML Result:** Test AUC 0.502 (LR), 0.502 (GBM) - RANDOM PERFORMANCE  

- **36 trades** (1.7/month)**Critical Finding:** News timing signal is REAL and STRONG (10.5x pips in test set), but ML cannot combine with technical features to predict individual trades

- **PF 1.680** (+51.4% vs baseline)

- **WR 44.44%**### News Filter Standalone Backtest (2025-11-11)

- **Avg 66.23 pips/trade****Approach:** Rule-based filter - trade ONLY near major events (no ML)  

- **All gates: ✅ PASS****Test Set Results (Out-of-Sample):**

- ✅ **9 trades** (2.4% of 374 test trades)

**Logic:** Trade when news is bearish but SuperTrend triggers → Catch oversold bounces- ✅ **66.67% win rate** (vs 37.97% baseline, +28.7pp)

- ✅ **156.63 avg pips** (vs 14.94 baseline, 10.5x multiplier)

---- ✅ **2.635 Profit Factor** (vs 1.110 baseline)

- ✅ Validation/Train showed similar advantage (9.0x Val, 4.2x Train)

#### Filter 2: strong_bullish (Momentum Strategy) 🆕

```python**Gates Assessment:**

headline_count >= 5 AND net_sentiment > 0.3- ✅ Test PF ≥ 1.25: PASS (2.635)

```- ✅ Test WR ≥ 38%: PASS (66.67%)

**Test Set Performance:**- ❌ Test trades ≥ 15: FAIL (only 9 trades)

- **104 trades** (5.0/month) - **3x more volume!**- ✅ PF improvement ≥ 5%: PASS (2.37x)

- **PF 1.266** (+14.1% vs baseline)

- **WR 45.19%****Conclusion:** News timing is highly predictive but current 111-event database provides insufficient trade frequency (only ~40 trades/year). Need expansion to 300-500 events for practical deployment.

- **Avg 32.81 pips/trade**

- **All gates: ✅ PASS**### Key Findings (All 5 Attempts)

- **News timing signal is REAL:** 10.5x pips advantage in test set when trading near major events

**Logic:** Trade when news + technicals both bullish → Follow momentum- **ML fundamentally fails:** Cannot predict individual trade outcomes even with:

  - 2,490 diverse trades (both long/short)

---  - 44 comprehensive features (technical + news sentiment)

  - 111 manually researched major market-moving events

#### Combined Strategy Option  - Look-ahead-free extraction (caught 2 bias incidents)

```python- **Root cause:** Trade outcomes driven by unpredictable factors beyond technical+news:

strong_bullish OR moderate_bearish  - Intraday order flow and institutional positioning

```  - Derivatives hedging activity

**Expected Performance:**  - Algorithmic execution patterns

- **~130-140 trades** (6-7/month)  - Stop loss trailing obscures entry quality (good entries can lose on stops)

- **Blended PF ~1.35-1.45**- **Sample size paradox:** News trades show massive advantage but too infrequent (9 test trades) for reliable ML training

- **Diversifies:** Momentum + Contrarian- **Binary classification wrong target:** Win/loss too noisy; winners/losers determined by exit timing more than entry quality



---### Lessons Learned

1. ✅ **News timing matters tremendously** - but works better as rule-based filter than ML feature

### Deployment Gates (All Passed ✅)2. ✅ **Technical features alone insufficient** - even 37 comprehensive indicators (RSI/MACD/BB/EMAs) couldn't predict

1. ✅ Count ≥ 20 trades3. ✅ **More data doesn't help** if signal doesn't exist (661→1,269→2,490 trades all failed)

2. ✅ Profit Factor ≥ 1.254. ✅ **Diversification helps signal discovery** but not enough (both-sides better than long-only, still failed)

3. ✅ Win Rate ≥ 38%5. ❌ **SuperTrend trailing stop obscures signal** - ML can't learn entry quality when exits dominate P&L

4. ✅ Improvement ≥ 10% vs baseline6. ❌ **Manual event coding has limits** - 111 events only cover 5.6% of trades (too sparse for ML)



---### Recommendation (Updated 2025-11-11)

**Pursue News-Based Trading with Frequency Expansion:**

### Key Lessons Learned1. **Immediate:** Expand event database from 111 → 300-500 events (add all NFP, CPI, FOMC meetings, jobless claims)

2. **Then:** Backtest expanded news filter (target 30-50 test trades instead of 9)

**What Worked:**3. **Alternative:** Use GDELT API to fetch real-time headlines for every trade window, build sentiment scoring

- Refined gold-specific queries (7x better relevance)4. **Fallback:** If frequency remains too low, remove EMA200 day filter to increase trade opportunities

- Contrarian + momentum signals5. **Abandon ML:** Accept that rule-based news filter >> ML predictions for this strategy

- Proper data validation (look-ahead bias check)

- Deployment gates prevent overfittingChecklist (Completed)

- [x] Freeze data snapshot & define time splits (Train 70% | Val 15% | Test 15%).

**What Didn't Work:**- [x] Extract baseline trades (15m K=2 combo) → 661 trades from combined results.

- ML prediction (5 failed attempts)- [x] Implement `scripts/ml/extract_features.py`:

- Generic GDELT queries (94% noise)- [x] Implement `scripts/ml/extract_features.py`:

- High volume without quality (baseline PF too low)  - [x] Load trades + underlying OHLC data.

  - [x] Generate features per trade:

---    - [x] Candle body % = |Close-Open| / (High-Low)

    - [x] Upper / lower wick %

## 🔄 IN PROGRESS    - [x] ATR(14) at entry (15m bars)

    - [x] Distance to EMA200 (pips & pct of ATR)

### Phase 3B: Implementation & Monitoring    - [x] Multi-timeframe Up-count (1m,5m,15m,30m,1h)

**Status:** In Progress      - [x] Hour-of-day

**Priority:** HIGH    - [x] Day-of-week

    - [x] Asian session range & breakout indicators

**Tasks:**    - [x] London open range

1. ⏳ Update strategy script to support bullish filter    - [x] Session flags

2. ⏳ Validate combined filter performance  - [x] Export parquet: `data/features/trades_features.parquet` (661 rows × 32 features)

3. ⏳ Deploy with monitoring dashboard- [x] Label definition v1: High-quality = pips > 0 (40% win rate).

4. ⏳ Real-time GDELT integration- [x] Time-based splits (70/15/15 no shuffle) & leakage check.

5. ⏳ Performance tracking (daily/weekly/monthly)- [x] Train baseline Logistic Regression → `ml/models/trade_quality_lr.pkl` (Test AUC 0.599).

- [x] Evaluate: ROC-AUC 0.599, Precision/Recall 0 (all negative predictions).

**Monitoring Metrics:**- [x] Train LightGBM upgrade → `ml/models/trade_quality_gbm.pkl` (Test AUC 0.516, overfitted).

- Trade frequency (target: 5-7/month)- [x] Probability threshold sweep (0.50→0.80 step 0.02) → Zero trades retained (all predictions <0.5).

- Profit factor (target: >1.25)- [x] Feature evaluation: Weak signals (MI <0.02), constant session flags removed.

- Win rate (target: >40%)- [x] Fixed critical session labeling bug (midnight timestamps instead of actual entry times).

- Max drawdown (alert if >2,000 pips)- [-] ~~Pick threshold meeting gates~~ — Not applicable (no useful threshold found).

- [-] ~~Integrate gating into `base_strategy.py`~~ — Deferred (gates not met).

---- [x] Report: `ml/reports/phase3a_results.md` (full analysis, probability distribution, overfitting diagnosis).



## 📋 PLANNED PHASESChecklist (Not Attempted - Gates Failed)

- [ ] Alternate label experiment: pips ≥ median win (record comparison).

### Phase 4: ML-Enhanced Entry System 🚀- [ ] Previous 5 trades mean pips feature

**Status:** Planning  - [ ] Previous 5 trades pips stdev feature

**Priority:** HIGH  - [ ] Win/loss streak length (signed) feature

**Goal:** Maximize trade volume (10-20/month) while maintaining quality (PF >1.3)- [ ] Initial stop distance (pips) feature

- [ ] Intraday range / 20-day median range feature

#### Objectives:

1. **Expand Trading Hours**Acceptance Gates (FAILED)

   - Current: 13-16 UTC only (NY overlap)- ❌ PF + ≥0.10 absolute vs baseline — Cannot measure (0 trades at P≥0.50).

   - Target: All 24 hours with time-aware features- ❌ Retain ≥60% of baseline trade count — 0% retained at P≥0.50.

   - Expected: 3-4x more opportunities- ❌ Retain ≥85% of top-decile winners — 0% retained at P≥0.50.



2. **Multi-Indicator Entry System**Artifacts Created

   - **Current:** SuperTrend only- `data/features/trades_features.parquet` — 661 trades × 32 features

   - **Add:**- `data/features/splits/train_indices.csv` — 462 trades (70%)

     - RSI (overbought/oversold, divergence)- `data/features/splits/val_indices.csv` — 99 trades (15%)

     - MACD (crossovers, histogram divergence)- `data/features/splits/test_indices.csv` — 100 trades (15%)

     - Volume analysis (high volume breakouts)- `ml/models/trade_quality_lr.pkl` — Logistic Regression model

     - Support/Resistance levels- `ml/models/trade_quality_gbm.pkl` — LightGBM model (overfitted)

     - Fibonacci retracements- `ml/models/metadata/*.json` — Model metadata (metrics, confusion matrices)

     - Bollinger Bands (volatility)- `ml/reports/feature_importance_gbm.csv` — Feature gain rankings

     - ATR-based volatility filters- `ml/reports/phase3a_results.md` — Comprehensive failure analysis

- `results/ml/features_univariate_summary.md` — Mutual information analysis

3. **Pattern Recognition**- `results/ml/features_quantile_pf.csv` — 5-bin PF by feature

   - Candlestick patterns (doji, engulfing, hammer, shooting star)- `results/ml/threshold_sweep_results.csv` — Empty sweep results

   - Multi-candle patterns (morning/evening star, three soldiers)

   - Chart patterns (double top/bottom, head & shoulders)---

   - Order flow imbalances## Phase 3A-R — ML Enhancement Roadmap (Revised)

   - Price action sequences

**Purpose:** Address root causes of Phase 3A failure before attempting ML again.

4. **ML Model Architecture**

   - **Input Features (~50-100):****Prerequisites:** Complete at least one item from Data Expansion AND Feature Engineering sections.

     - Technical indicators (RSI, MACD, Stoch, ADX, etc.)

     - Price patterns (candle types, sequences)### 1. Data Expansion (Critical Priority)

     - Time features (hour, day, session, volatility regime)

     - Market structure (S/R proximity, trend strength)**Goal:** Increase trade diversity from 661 homogeneous trades → 2000+ diverse samples

     - News sentiment (keep our GDELT features)

     - Volume profileChecklist

   - [ ] **Multi-timeframe expansion:**

   - **Target Variable:**   - [ ] Run 5m SuperTrend backtest (same K=2 logic) → target 300+ trades

     - Binary: Trade quality (1 if PF >1.5, 0 otherwise)  - [ ] Run 30m SuperTrend backtest → target 200+ trades

     - Or regression: Expected pips  - [ ] Run 1h SuperTrend backtest → target 150+ trades

     - [ ] Combine all timeframes into unified dataset with `timeframe` feature

   - **Model Types to Test:**- [ ] **Parameter sweep expansion:**

     - XGBoost/LightGBM (tree-based, interpretable)  - [ ] Test ST period variations: 8, 10, 12 (currently 10) × 3 timeframes → 9 combinations

     - Neural Network (deep patterns)  - [ ] Test ST multiplier variations: 3.0, 3.3, 3.6, 4.0 (currently 3.6) × 3 timeframes → 12 combinations

     - Ensemble (combine multiple models)  - [ ] Collect all "reasonable PF" variants (PF >1.0) into dataset

- [ ] **Strategy diversification (optional, long-term):**

5. **High-Volume Strategy**  - [ ] Add EMA crossover strategy (50/200 cross)

   - Target: 10-20 trades/month (vs current 5/month)  - [ ] Add breakout strategy (Asian range breakout)

   - Maintain: PF >1.3, WR >38%  - [ ] Add mean reversion strategy (Bollinger Band bounces)

   - Approach: More entry opportunities + better filtering- [ ] **Validation:** Target ≥2000 trades with variance in entry conditions, timeframes, market regimes

   - Trade multiple sessions (Asia, London, NY)

### 2. Feature Engineering (High Priority)

#### Research Areas:

- **Time-Based Patterns:** Which hours produce best trades?**Goal:** Capture non-linear patterns and threshold effects revealed in Phase 3A analysis

- **Indicator Combinations:** Which indicators complement SuperTrend?

- **Pattern Effectiveness:** Do certain candlestick patterns actually work?Checklist

- **Regime Detection:** Different strategies for trending vs ranging markets?- [ ] **Regime-based features:**

  - [ ] `up_count_regime`: Binned (low=1-2, med=3, high=4-5) — Phase 3A found low consensus PF 1.47 vs high 1.16

#### Implementation Plan:  - [ ] `hour_bucket`: Categorical (overlap=13-16, ny=16-20, quiet=other)

1. **Feature Engineering** (Week 1-2)  - [ ] `volatility_regime`: Daily ATR percentile (rolling 20-day)

   - Extract 50-100 technical features  - [ ] `trend_strength`: EMA200 slope / ATR (normalized momentum)

   - Pattern recognition library- [ ] **Distance/breakout features (ATR-normalized):**

   - Time-based features  - [ ] `dist_to_asian_high_atr`: (close - asian_high) / atr14

     - [ ] `dist_to_asian_low_atr`: (asian_low - close) / atr14

2. **Data Labeling** (Week 2)  - [ ] `dist_to_london_open_atr`: Distance from London open price

   - Label trade quality on historical data  - [ ] `range_expansion_pct`: Current range / 20-day median range

   - Split: 70/15/15 (train/val/test)- [ ] **Interaction features:**

     - [ ] `up_count_x_hour`: Capture "low consensus in overlap session" pattern

3. **Model Development** (Week 3-4)  - [ ] `atr_x_range_expansion`: Volatility context (expanding vs contracting)

   - Train multiple model types  - [ ] `ema_dist_x_trend_strength`: Strong trend with close alignment

   - Hyperparameter optimization- [ ] **Momentum indicators (test for incremental value):**

   - Cross-validation  - [ ] RSI(14) at entry (overbought/oversold context)

     - [ ] MACD histogram at entry (momentum divergence)

4. **Backtesting** (Week 4)  - [ ] Note: Only add if MI > 0.02 or improves model AUC >0.03

   - Walk-forward validation- [ ] **Sequence features:**

   - Compare to current filters  - [ ] Previous 3 trades mean pips (recent performance context)

   - Deployment gates check  - [ ] Consecutive wins/losses (streak length, signed)

     - [ ] Bars since last trade (trade frequency context)

5. **Deployment** (Week 5)- [ ] **Validation:** Re-run `evaluate_features.py` on expanded dataset; verify MI scores >0.02 for engineered features

   - Real-time inference

   - Monitoring dashboard### 3. Model Improvements

   - A/B testing vs news filter

**Goal:** Address overfitting and calibration issues

#### Success Criteria:

- ✅ 10-20 trades/month (2-4x current volume)Checklist

- ✅ PF >1.3 (maintain quality)- [ ] **Regularization & hyperparameter tuning:**

- ✅ WR >38% (better than baseline)  - [ ] LightGBM: Reduce max_depth (try 3, 4 vs default 6), increase min_child_samples (20, 50)

- ✅ Works across all trading sessions  - [ ] Add early stopping (20 rounds no improvement on validation)

- ✅ Interpretable feature importance  - [ ] L2 regularization (lambda_l2 = 1.0, 5.0)

- [ ] **Probability calibration:**

---  - [ ] Apply isotonic or Platt calibration to Logistic Regression (fix underconfident predictions)

  - [ ] Check if calibrated probabilities span 0.3-0.7 range (vs current 0.26-0.47)

### Phase 5: Multi-Timeframe & Multi-Instrument- [ ] **Alternative models (if LightGBM continues overfitting):**

**Status:** Future    - [ ] Random Forest with max_depth=5, min_samples_leaf=20 (more conservative)

**Priority:** MEDIUM  - [ ] XGBoost with stricter regularization

  - [ ] Ensemble: Average Logistic + calibrated tree model

**Objectives:**- [ ] **Cross-validation:** 5-fold time-series CV instead of single 70/15/15 split (more robust validation)

1. Deploy same strategy on 5m, 15m bars (3x trades)

2. Expand to EURUSD, GBPUSD with adapted news filters### 4. Experimental: Daily Regime Pre-Filter (Phase 3B Simplified)

3. Portfolio-level risk management

4. Correlation filters**Goal:** Filter out entire bad days before individual trade scoring



**Expected:** 15-30 trades/month across instrumentsChecklist

- [ ] **Aggregate daily features:**

---  - [ ] EMA200 distance z-score (mean across 5 timeframes)

  - [ ] Up-count ratio: # timeframes up / total (consensus measure)

### Phase 6: Advanced Risk Management  - [ ] Daily volatility: First-hour ATR vs 20-day median

**Status:** Future    - [ ] Prior 3-day strategy pips (momentum)

**Priority:** MEDIUM- [ ] **Label:** Good day = daily total pips > 0 (binary classification)

- [ ] **Model:** Logistic Regression or simple decision tree (interpretable)

**Objectives:**- [ ] **Integration:** Skip all trades on days predicted as "bad" (P(good) <0.4)

1. Position sizing based on ATR volatility- [ ] **Validation:** Check if filtering improves PF +0.05 and reduces max DD >5%

2. Drawdown-based cooldowns (pause after -500 pips)

3. Correlation filters (avoid correlated positions)### 5. Alternative: Rule-Based Filter (Non-ML Fallback)

4. Maximum concurrent positions limit

5. Time-based exposure limits**Goal:** Simple heuristics from Phase 3A insights



**Expected:** Reduce max drawdown 30-50%Checklist

- [ ] **Rule 1:** Skip trades with `up_count ≥ 4` (high consensus = lower PF per quantile analysis)

---- [ ] **Rule 2:** Only take trades during `hour 13-16` (overlap session peak)

- [ ] **Rule 3:** Require `sec_asia_range_atr < 0.8` (low volatility setup)

## 📊 Performance Tracking- [ ] **Rule 4:** Skip if `ema_dist_atr > 2.0` (too extended from trend)

- [ ] **Backtest:** Combine rules, measure PF improvement vs baseline

### Current Best Results (Test Set)- [ ] **Compare:** Rule-based vs ML models (if rules outperform, accept simpler solution)



| Strategy | Trades | PF | WR | Avg Pips | Monthly Freq |### Acceptance Gates (Revised for Phase 3A-R)

|----------|--------|----|----|----------|--------------|

| Baseline | 374 | 1.110 | 37.97% | 14.94 | 17.8 |Must meet ONE of the following:

| **strong_bullish** | **104** | **1.266** | **45.19%** | **32.81** | **5.0** ✅ |

| moderate_bearish | 36 | 1.680 | 44.44% | 66.23 | 1.7 |**Option A: ML Model Success**

| Combined (est.) | ~140 | ~1.40 | ~44% | ~45 | ~6-7 |- Test AUC ≥0.65 (moderate discrimination)

- PF improvement ≥+0.10 vs baseline (1.16 → 1.26)

### Targets for Phase 4 (ML Entry System)- Retain ≥60% of baseline trade count

- Retain ≥85% of top-decile winners

| Metric | Current | Phase 4 Target | Stretch Goal |- Predictions span 0.3-0.7 probability range (no severe calibration issues)

|--------|---------|----------------|--------------|

| Trades/Month | 5 | 10-15 | 20 |**Option B: Rule-Based Success**

| Profit Factor | 1.266 | 1.30+ | 1.50+ |- PF improvement ≥+0.08 vs baseline (1.16 → 1.26)

| Win Rate | 45.19% | 40%+ | 45%+ |- Retain ≥50% of baseline trade count (simpler rules = more aggressive filtering acceptable)

| Avg Pips | 32.81 | 25+ | 40+ |- Max DD reduction ≥5%



---**Option C: Accept Baseline**

- If neither A nor B achieved after Data Expansion + Feature Engineering iteration

## 🛠️ Technical Stack- Document that 15m K=2 baseline is near-optimal, proceed to live trading



### Current Tools:---

- **Data:** Twelve Data API, GDELT Doc API## Phase 3A-R — ML Enhancement Roadmap (Revised)

- **Analysis:** Python, pandas, numpy

- **ML:** transformers (FinBERT), scikit-learn**Purpose:** Address root causes of Phase 3A failure before attempting ML again.

- **Visualization:** Plotly

- **Backtesting:** Custom framework**Prerequisites:** Complete at least one item from Data Expansion AND Feature Engineering sections.



### Phase 4 Additions:### 1. Data Expansion (Critical Priority)

- **Feature Engineering:** ta-lib, pandas-ta

- **ML:** XGBoost, LightGBM, TensorFlow/PyTorch**Goal:** Increase trade diversity from 661 homogeneous trades → 2000+ diverse samples

- **Pattern Recognition:** OpenCV, custom algorithms

- **Hyperparameter Tuning:** OptunaChecklist

- **Monitoring:** MLflow, custom dashboards- [ ] **Multi-timeframe expansion:**

  - [ ] Run 5m SuperTrend backtest (same K=2 logic) → target 300+ trades

---  - [ ] Run 30m SuperTrend backtest → target 200+ trades

  - [ ] Run 1h SuperTrend backtest → target 150+ trades

## 📁 Repository Structure  - [ ] Combine all timeframes into unified dataset with `timeframe` feature

- [ ] **Parameter sweep expansion:**

```  - [ ] Test ST period variations: 8, 10, 12 (currently 10) × 3 timeframes → 9 combinations

XAUI/  - [ ] Test ST multiplier variations: 3.0, 3.3, 3.6, 4.0 (currently 3.6) × 3 timeframes → 12 combinations

├── data/  - [ ] Collect all "reasonable PF" variants (PF >1.0) into dataset

│   ├── combined_xauusd_1min_full.csv          # Main price data- [ ] **Strategy diversification (optional, long-term):**

│   ├── features/  - [ ] Add EMA crossover strategy (50/200 cross)

│   │   └── trades_sentiment_gold_clean.parquet # Clean sentiment features  - [ ] Add breakout strategy (Asian range breakout)

│   └── trend/  - [ ] Add mean reversion strategy (Bollinger Band bounces)

│       └── ema200_trend_by_date_*.csv          # Trend filters- [ ] **Validation:** Target ≥2000 trades with variance in entry conditions, timeframes, market regimes

├── sentiments/

│   ├── fetch_news_gdelt.py                     # GDELT fetcher### 2. Feature Engineering (High Priority)

│   └── news/

│       └── headlines_gold_specific_clean.csv   # Clean headlines**Goal:** Capture non-linear patterns and threshold effects revealed in Phase 3A analysis

├── scripts/

│   ├── base_strategy.py                         # Original SuperTrendChecklist

│   ├── strategy_with_news_filter.py            # News-filtered version

│   ├── generate_ema200_trend.py                # Trend filter generator---

│   └── ml/## Phase 3B — Daily Regime Scoring

│       ├── analyze_gdelt_sentiment.py          # FinBERT analyzer

│       └── backtest_gdelt_filter.py            # Filter validation**Status: DEFERRED** — Awaiting Phase 3A-R completion (requires expanded dataset)

├── results/

│   ├── ml/gdelt_clean_backtest/                # Backtest resultsPurpose: Rate each day (Strong / Neutral / Avoid) pre-market. Skip or downsize weak days.

│   └── news_filtered/                          # Strategy outputs

├── docs/Checklist

│   ├── PHASE_3A_FINAL_SUCCESS.md               # Phase 3A summary- [ ] Build daily feature set script `scripts/build_daily_regime_features.py`:

│   ├── NEWS_FILTER_TEST_RESULTS.md             # Test set analysis  - EMA distance z-scores per TF (1m,5m,15m,30m,1h).

│   ├── CLEAN_DATA_RESULTS.md                   # Look-ahead bias fix  - EMA slope normalized by ATR.

│   └── HIGHER_VOLUME_OPTIONS.md                # Volume analysis  - Volatility compression: intraday range / 20-day median range.

└── plan.md                                      # This file  - Up-count ratio (# Up / total TFs).

```  - Prior 3-day cumulative strategy pips.

  - Rolling equity slope (regression over last 50 trades’ cumulative pips).

---- [ ] Labeling:

  - Strong: day total pips > 75th percentile.

## 🎯 Next Immediate Actions  - Neutral: 25th–75th percentile.

  - Avoid: <25th percentile or negative.

1. **Deploy strong_bullish filter** (this week)- [ ] Train classifier (LightGBM multi-class) → `ml/models/day_regime.pkl`.

   - Update strategy script ✅- [ ] Derive regime score = P(Strong).

   - Run combined filter test ✅- [ ] Threshold experiments for skipping Avoid days; document PF, DD, trade count impact.

   - Set up monitoring- [ ] Integrate gating:

   - Document deployment  - Flags: `--regime-filter ml/models/day_regime.pkl` & `--regime-threshold <t>`.

  - Size tiers (optional): Strong=1.0, Neutral=0.7, Avoid=0.

2. **Phase 4 Research** (next 2 weeks)- [ ] Report: `ml/reports/daily_regime_metrics_<date>.md` (confusion matrix, PF/DD table per regime).

   - Literature review on ML entry systems

   - Feature engineering frameworkAcceptance Gates

   - Gather additional indicator libraries- Max DD reduction ≥10% vs ungated baseline.

   - Design ML pipeline architecture- PF neutral or improved.

- Retain ≥50% of trades.

3. **Data Collection** (ongoing)

   - Continue GDELT monitoring---

   - Validate real-time API reliability## Phase 3C — Quantile / Distribution-Based Sizing

   - Archive daily for retraining

**Status: DEFERRED** — Awaiting Phase 3A-R completion (requires expanded dataset)

---

Purpose: Predict downside (risk) and upside (reward) ranges; size trades where reward outweighs risk.

## 📈 Success Metrics

Checklist

### Phase 3 (Current) - ✅ ACHIEVED- [ ] Extend feature set (add time since last signal, prior day range, ATR trend slope).

- [x] Find profitable news filter- [ ] Train quantile model (LightGBM quantile or NGBoost): predict Q20, Q50, Q80 pips.

- [x] Pass all deployment gates- [ ] Compute score = Q50 / |Q20| per trade.

- [x] Improve PF by >10%- [ ] Size map: score <0.8 → 0.5x; 0.8–1.2 → 1.0x; >1.2 → 1.3x (cap).

- [x] Achieve >5 trades/month- [ ] Daily VAR check: sum(size * |Q20|) ≤ predefined limit.

- [ ] Drawdown safety: disable >1.0x sizing if current equity DD > threshold.

### Phase 4 (ML Entry System) - 🎯 TARGET- [ ] Integrate sizing flag: `--quantile-model ml/models/quantile_sizing.pkl --sizing-enabled`.

- [ ] 10-20 trades/month- [ ] Simulated curve vs baseline; compute Sharpe, max DD, worst trade impact.

- [ ] PF >1.30- [ ] Report: `ml/reports/quantile_sizing_metrics_<date>.md`.

- [ ] WR >40%

- [ ] Works all hours (not just 13-16 UTC)Acceptance Gates

- [ ] Interpretable model (feature importance)- Sharpe ≥ +15% vs baseline.

- Max DD not worse.

### Long-term Goals- Worst trade magnitude not larger than baseline worst.

- [ ] 20+ trades/month per instrument

- [ ] Multi-instrument portfolio (3+ pairs)---

- [ ] PF >1.50 system-wide## Monitoring & Drift Control

- [ ] Automated deployment pipeline

- [ ] Real-time monitoring dashboardChecklist

- [ ] Implement `scripts/monitor_ml.py`:

---  - Weekly PF, Sharpe, retention %, regime distribution.

  - Drift signals: probability compression (std < threshold), retention collapse (<40%).

## 📝 Notes & Insights  - Auto-generate `ml/reports/drift_alert_<date>.md` on anomalies.

- [ ] Adaptive threshold logic (optional): recalibrate every 4 weeks if PF drop > set %.

### Critical Learnings:- [ ] Fallback: disable ML layers automatically if drift alert persists 2 consecutive weeks.

1. **Data quality matters more than model complexity**

   - Look-ahead bias invalidated first results---

   - Refined queries (42% relevant) >> generic (6% relevant)## Versioning & Reproducibility



2. **Simple rules can outperform ML**Checklist

   - 5 ML attempts failed- [ ] `ml/README.md` summarizing each model (features, date, metrics, threshold).

   - Simple sentiment thresholds succeeded- [ ] Save `feature_schema_trade_quality.json`, `feature_schema_regime.json`.

- [ ] Include training parameters JSON per model.

3. **Volume vs Quality trade-off is real**- [ ] Store dataset slice hash (commit hash + date range).

   - Can't have 20 trades/month at PF 1.7- [ ] Maintain changelog inside `ml/README.md`.

   - But can have 5 trades/month at PF 1.26 ✅

---

4. **Deployment gates prevent overfitting**## Risk Controls (Integration Points)

   - Forced proper validation

   - Caught look-ahead biasChecklist

- [ ] Max consecutive rejected trades watchdog (adjust threshold downward if triggered).

5. **Multiple strategies > single strategy**- [ ] Cooldown: pause new trades N bars after equity DD > X.

   - Bullish + Bearish diversifies- [ ] Emergency bypass flag: `--disable-ml`.

   - Different market regimes need different approaches- [ ] Logging: structured JSON per run capturing ML decisions.



### Future Research Questions:---

- Can ML identify regime changes for strategy switching?## Current Status Table

- Are there patterns that predict high-quality trades?

- Which hours have best risk/reward for gold?| Component                | Status    | Notes |

- Do certain indicator combinations reduce false signals?|--------------------------|-----------|-------|

| Baseline 15m + K=2       | ✅ DONE   | PF 1.16, 448 trades, max DD -6040 pips |

---| Feature Extraction (3A)  | ✅ DONE   | 661 trades × 32 features, session bug fixed |

| Trade Quality Models     | ❌ FAILED | Test AUC 0.599 (LR), 0.516 (GBM), no useful threshold |

**Last Updated:** November 12, 2025  | Phase 3A-R Roadmap       | 📋 PLANNED | Data expansion + feature engineering path defined |

**Current Phase:** 3B (Deployment) + 4 (ML Research)  | Regime Scoring (3B)      | ⏸️ DEFERRED | Awaiting 3A-R completion |

**Next Milestone:** Deploy strong_bullish, begin Phase 4 ML development| Quantile Sizing (3C)     | ⏸️ DEFERRED | Awaiting 3A-R completion |

| Monitoring / Drift       | PENDING   | |
| Risk Controls            | PENDING   | |
| Versioning Artifacts     | PENDING   | |

---
## Execution Order (Recommended — Updated 2025-11-11)

### ✅ COMPLETED
1. ✅ Feature extraction script & dataset parquet (661 trades - Attempt 1)
2. ✅ Logistic regression baseline + threshold sweep (failed gates - Attempt 1)
3. ✅ LightGBM trade quality model (overfitted - Attempt 1)
4. ✅ Data expansion to 1,269 trades (Attempt 2 - worse results)
5. ✅ Both-sides strategy backtest: 2,490 trades, PF 1.13 (Attempt 3 setup)
6. ✅ Enhanced technical features: 37 indicators (RSI/MACD/BB/EMAs/momentum) (Attempt 4 - failed)
7. ✅ Manual news events database: 111 major events 2015-2025 (Attempt 5 - failed ML)
8. ✅ News filter standalone backtest: 10.5x pips advantage confirmed (insufficient frequency)
9. ✅ GDELT API setup and sample headline fetch

### 🔄 IN PROGRESS (Phase 3A-Next)
10. 📋 **CURRENT: Create events_offline.csv for all 2,490 trades**
11. 📋 **NEXT: Fetch GDELT headlines for all trade windows**
12. 📋 Build sentiment analysis pipeline
13. 📋 Remove EMA200 filter and backtest all-days strategy (~5,500 trades)

### 📋 PLANNED (Immediate Priority)
14. Backtest GDELT headline filter (target ≥20 test trades)
15. Feature extraction on expanded all-days dataset (~5,500 trades)
16. News filter on expanded dataset (target ~300 affected trades)
17. Validate gates: Test trades ≥20, PF ≥1.25, WR ≥38%
18. **DECISION POINT:** Deploy news filter OR accept baseline without filter

### ⏸️ DEFERRED (If News Expansion Successful)
19. Daily regime feature build + classifier & gating (Phase 3B)
20. Quantile sizing model & simulation (Phase 3C)
21. Monitoring / drift script
22. Risk controls & adaptive thresholds
23. Versioning & README finalization

### ❌ ABANDONED
- Multi-timeframe ML expansion (proven ineffective after 5 attempts)
- Parameter sweep for ML (more data doesn't help without signal)
- Individual trade quality prediction via ML (binary classification wrong target)

---

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

