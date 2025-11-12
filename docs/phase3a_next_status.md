# Phase 3A-Next Status Update

**Date:** 2025-11-11  
**Status:** Ready to Execute

## What We Accomplished Today

### 1. ✅ Comprehensive ML Failure Analysis
- Documented 5 failed attempts at trade quality prediction
- **Final Result:** Even with 111 major events, 44 features, 2,490 trades → Test AUC 0.502 (random)
- **Key Discovery:** News timing signal is REAL (10.5x pips advantage) but ML cannot combine features

### 2. ✅ News Filter Standalone Validation  
**Test Set Results (Out-of-Sample):**
- 9 trades near major events (vs 365 without)
- 66.67% WR (vs 37.97% baseline, +28.7pp)
- 156.63 avg pips (vs 14.94 baseline, **10.5x multiplier**)
- 2.635 Profit Factor (vs 1.110 baseline)

**Problem:** Only 9 test trades (too infrequent for practical deployment)

### 3. ✅ Updated Plan Document
**Added Linear History:** Clear chronological narrative of all 5 ML attempts with results
**Added Phase 3A-Next:** Two-pronged approach to increase trade frequency:
1. GDELT real-time headline integration
2. Remove EMA200 day filter (trade all days)

### 4. ✅ GDELT Infrastructure Setup
**Created:** 
- `scripts/ml/create_gdelt_events.py` — Generate event windows for all trades
- `sentiments/news/events_offline.csv` — 2,490 trade windows with 3-hour lookback
- Ready to fetch headlines via existing `sentiments/fetch_news_gdelt.py`

### 5. ✅ Strategy Expansion Implementation
**Modified:** `scripts/base_strategy.py`
- Added `--ignore-ema-filter` flag
- When set: trades SuperTrend patterns on ALL days (not just EMA200 up-trend days)
- Expected: ~5,500 trades (vs current 2,490) = 2.2x increase

## Next Steps (In Priority Order)

### Step 1: Run All-Days Backtest (IMMEDIATE)
```bash
python scripts/base_strategy.py \
  --input-csv data/combined_xauusd_1min_full.csv \
  --both-sides \
  --ignore-ema-filter \
  --entry-hours 13-16 \
  --run-tag "all_days_both_sides"
```

**Expected Output:**
- ~5,500 trades (trading every day during London/NY overlap)
- Check baseline PF (target ≥1.05)
- Validate long/short balance
- Output: `results/baseline_2015_2025_all_days_both_sides/15m/trades.csv`

### Step 2: Apply Manual News Filter to Expanded Dataset
```bash
python scripts/ml/extract_news_sentiment.py \
  --trades-csv results/baseline_2015_2025_all_days_both_sides/15m/trades.csv \
  --out-parquet data/features/trades_news_sentiment_5500.parquet

python scripts/ml/backtest_news_filter.py \
  --features-parquet data/features/trades_features_5500_with_news.parquet \
  --out-dir results/ml/news_filter_expanded_backtest
```

**Expected Output:**
- ~300 trades near 111 major events (vs current 140)
- Test set: ~30-40 trades (vs current 9)
- If ≥20 test trades with PF ≥1.25 → **DEPLOY**

### Step 3: Fetch GDELT Headlines (PARALLEL TRACK)
```bash
# This will take ~2-3 hours with throttling (2,490 API calls @ 0.3 sec each)
python sentiments/fetch_news_gdelt.py \
  --events-csv sentiments/news/events_offline.csv \
  --out-csv sentiments/news/headlines_raw.csv \
  --max-events 2490 \
  --throttle-sec 0.3
```

**Expected Output:**
- 50K-150K headlines across 2,490 trade windows
- Average ~20-60 headlines per trade window
- Output: `sentiments/news/headlines_raw.csv`

### Step 4: Build Sentiment Pipeline (After Step 3)
```python
# Create scripts/ml/analyze_gdelt_sentiment.py
# 1. Classify headlines (gold-bullish/bearish/neutral)
# 2. Count high-impact headlines per window
# 3. Compute aggregate sentiment scores
# 4. Extract features: headline_count, bullish_pct, net_sentiment
```

### Step 5: Validate GDELT Filter
- Rule: Trade only if `headline_count ≥5` AND `|net_sentiment| >0.3`
- Target: ≥20 test trades, PF ≥1.25, WR ≥38%

## Decision Tree

```
Current State: 2,490 trades, 9 test near events (TOO LOW)
│
├─ Path 1: All-Days Strategy (Steps 1-2)
│  ├─ Run: ~5,500 trades baseline
│  ├─ Filter: 111 events → ~300 affected → ~30-40 test trades
│  └─ If test trades ≥20 & PF ≥1.25 → **DEPLOY NEWS FILTER**
│
├─ Path 2: GDELT Headlines (Steps 3-5)
│  ├─ Fetch: 2,490 windows × ~40 headlines = 100K headlines
│  ├─ Classify: Build sentiment scores
│  ├─ Filter: headline_count ≥5 → ~500-800 affected trades
│  └─ If test trades ≥20 & PF ≥1.25 → **DEPLOY GDELT FILTER**
│
└─ Path 3: Hybrid (Both)
   ├─ Combine: 5,500 trades + GDELT headlines
   ├─ Filter: Both pattern + news
   └─ Target: ~1,000 trades with news, 100+ in test
```

## Files Created/Modified

### Created
- `scripts/ml/backtest_news_filter.py` — Standalone news filter backtest with gates
- `scripts/ml/create_gdelt_events.py` — Generate event windows for GDELT fetching
- `scripts/ml/merge_features_v2.py` — Proper timezone-aware feature merging
- `sentiments/news/events_offline.csv` — 2,490 trade windows for headline fetching
- `results/ml/news_filter_backtest/` — Backtest results (9 test trades, 10.5x pips)

### Modified
- `plan.md` — Added complete linear history, Phase 3A-Next action items
- `scripts/base_strategy.py` — Added `--ignore-ema-filter` flag for all-days trading
- `scripts/ml/extract_news_sentiment.py` — 111-event comprehensive database (up from 26)

## Key Metrics to Watch

### Baseline (Current)
- Trades: 2,490
- PF: 1.13
- Test trades near events: 9
- Test PF (news only): 2.635
- Test WR (news only): 66.67%

### Targets (Post-Expansion)
- **Frequency Gate:** ≥20 test trades with news
- **Performance Gate:** Test PF ≥1.25, WR ≥38%
- **Quality Gate:** Baseline all-days PF ≥1.05
- **GDELT Gate:** ≥80% of trades have ≥3 relevant headlines

## Risk Factors

1. **All-days trading might lower PF:** Non-trending days could have worse performance
   - Mitigation: Add minimum ATR threshold if needed
   
2. **GDELT headlines quality:** May have noise, irrelevant articles
   - Mitigation: Strict keyword filtering ("gold", "inflation", "fed", "yields")
   
3. **Stop loss effectiveness:** Need to validate stops work in both directions
   - Mitigation: Analyze worst trades, adjust if needed
   
4. **Overfitting to test period:** 2023-2025 may differ from 2015-2022
   - Mitigation: Separate validation period, walk-forward testing

## Success Criteria

**DEPLOY if ANY of:**
1. All-days + manual events: ≥20 test trades, PF ≥1.25
2. Current data + GDELT: ≥20 test trades, PF ≥1.25
3. All-days + GDELT: ≥30 test trades, PF ≥1.20

**ABANDON NEWS FILTER if:**
- All paths yield <15 test trades
- OR test PF <1.15
- OR implementation complexity >2 weeks

**Fallback:** Accept baseline PF 1.13 without filter, move to Phase 4 (portfolio management)
