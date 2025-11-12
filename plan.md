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

# XAUI Project Plan (Slim)

Last updated: 2025-11-12

## Overview

Goal: Trade XAUUSD using a 1-minute SuperTrend strategy enhanced with a news-sentiment filter. Keep code and docs minimal, production-focused.

Status: Validated and ready for paper deployment. Live after 2 weeks if metrics hold.

## Validated Strategy (Production)

- Timeframe: 1-minute entries, trade window 13:00–16:00 UTC
- Entry logic: SuperTrend flip + alternating candle (base_strategy.py)
- Exit logic: Cross back through SuperTrend (with capped SL distance)
- Trend filter: Daily EMA200 trend (Up/Down) file (generate_ema200_trend.py)
- News filter: Combined sentiment (bearish OR bullish)
  - min headlines ≥ 5
  - bearish: net_sentiment < -0.1
  - bullish: net_sentiment > 0.3

Performance (Test set: 2024-01-10 → 2025-10-14):
- Combined filter: 140 trades (6.7/mo), PF 1.355, WR 45.0%, avg +41.40 pips, DD -2,079 pips
- Bullish-only: 104 trades, PF 1.266, WR 45.19%, avg +32.81 pips
- Bearish-only: 36 trades, PF 1.680, WR 44.44%, avg +66.23 pips

Decision: Use COMBINED filter in production (best balance of volume + edge).

## Data (Keep)

- Price: data/combined_xauusd_1min_full.csv (UTC, 1m OHLC)
- Trend: data/ema200_trend_by_date.csv
- Clean news: sentiments/news/headlines_gold_specific_clean.csv
- Features: data/features/trades_sentiment_gold_clean.parquet

Note: Old/biased headlines and intermediate features removed.

## Minimal Code (Keep)

- scripts/base_strategy.py — SuperTrend core
- scripts/strategy_with_news_filter.py — integrates sentiment filter
- scripts/generate_ema200_trend.py — trend file creation
- scripts/deploy_live_strategy.py — deploy + monitor setup
- scripts/monitor_performance.py — live dashboard & reports
- scripts/ml/analyze_gdelt_sentiment.py — build sentiment features
- scripts/ml/backtest_gdelt_filter.py — validate filters
- scripts/ml/create_gdelt_events.py — fetch/build events
- scripts/ml/check_news.py — data sanity checks

Removed: Legacy ML training/tuning/old feature scripts and one-off utilities.

## How to Run

Backtest quick check (news filter):
- python scripts/strategy_with_news_filter.py --use-news-filter --filter-type combined --both-sides --entry-hours 13-16 --date-start 2024-01-10

Paper deploy:
- python scripts/deploy_live_strategy.py --mode paper --validate
- python scripts/monitor_performance.py --mode paper --plot --export report.html

Live (after paper validation):
- python scripts/deploy_live_strategy.py --mode live

Success gates (live): after ≥20 trades
- Profit Factor ≥ 1.25
- Win Rate ≥ 38%
- Max DD ≤ 2,500 pips

## Monitoring

Daily
- Trade count, WR, PF, total pips, drawdown

Weekly
- HTML report + equity curve
- Alert if PF < 1.20 or WR < 35% (≥20 trades)

Monthly
- Rolling 90-day revalidation and thresholds review

## Phase 4 (Next)

Objective: Lift volume to 10–20 trades/month at PF ≥ 1.30.

Scope
- Expand beyond 13–16 UTC (all sessions)
- Add technical features: RSI/MACD/divergence, volatility, structure
- Pattern recognition: candlesticks, ranges, breakouts
- ML model (XGBoost/LightGBM) to score trade quality

Milestones
1. Feature set (50–100 features) + label design (2 weeks)
2. Model training/tuning + walk-forward (2 weeks)
3. Paper deploy + monitoring (1 week)

KPIs
- 10–20 trades/month; PF ≥ 1.30; WR ≥ 40%; stable across hours

## Repository (Slim)

- data/ (price, trend, features)
- sentiments/news/ (clean headlines)
- scripts/ (minimal production + core ML build scripts)
- results/combined/, results/ml/gdelt_clean_backtest/
- docs/ (deployment, comparisons, volume analysis)
- README.md, plan.md

## Notes

- Keep code and docs lean. Prefer stability and repeatability over breadth.
- Re-validate quarterly; adjust thresholds if drift is detected.


### Phase 4: ML-Enhanced Entry System 🚀- [ ] Previous 5 trades mean pips feature
