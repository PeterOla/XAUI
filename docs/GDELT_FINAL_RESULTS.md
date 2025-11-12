# GDELT + Sentiment Analysis - Final Results & Diagnosis

## Executive Summary

**Status:** ✅ Infrastructure Complete, ⚠️ Filter Performance Below Target

### What We Built
- ✅ GDELT fetcher: 478K headlines across 1,924 trades (77% coverage)
- ✅ FinBERT sentiment analyzer: 12 features per trade
- ✅ Comprehensive backtest framework: 11 different filters tested

### Results
- ❌ **No filters pass deployment gates** (PF ≥1.25, WR ≥38%, count ≥20)
- ❌ Best filter PF 1.109 vs baseline 1.110 (essentially no improvement)
- ❌ Strong directional filters (sentiment >0.3 or <-0.3): **ZERO trades**

### Root Cause
**Headlines are too generic and mostly neutral:**
- Only **5.9%** of headlines mention "gold"
- Only **2.4%** mention "Fed"
- Only **3.8%** mention "inflation"
- Average net_sentiment: **-0.014** (nearly zero)
- Sentiment breakdown: 61% neutral, 18.5% bullish, 20.3% bearish

## Detailed Results

### GDELT Fetch Statistics
```
Total headlines: 478,181
Unique events: 1,924
Coverage: 77% of trades (2017-2025)
Avg headlines per trade: 248.5 (capped at 250 by API)
Headlines per event: 192 average after filtering
```

### Sentiment Analysis Results
```
Trades with headlines: 1,924 (77%)
Trades with ≥5 headlines: 1,924 (100% of those with news)
Avg bullish count: 35.5 per trade (18.5%)
Avg bearish count: 39.0 per trade (20.3%)
Avg neutral count: 117.6 per trade (61.2%)
Net sentiment: -0.014 (essentially zero)
```

### Backtest Results (Test Set, n=374)

| Filter | Count | Win Rate | Avg Pips | Profit Factor | Gates Pass |
|--------|-------|----------|----------|---------------|------------|
| **Baseline** | 374 | 37.97% | 14.94 | **1.110** | - |
| has_news (≥5 headlines) | 371 | 38.01% | 14.72 | 1.109 | ❌ |
| high_coverage (≥10) | 371 | 38.01% | 14.72 | 1.109 | ❌ |
| very_high_coverage (≥20) | 371 | 38.01% | 14.72 | 1.109 | ❌ |
| gold_focused (≥5 gold mentions) | 359 | 37.88% | 12.35 | 1.091 | ❌ |
| moderate_directional (abs >0.1) | 54 | 35.19% | -47.39 | 0.656 | ❌ |
| **strong_directional (abs >0.3)** | **0** | - | - | - | **❌** |

### Deployment Gates Status

All filters FAIL at least one gate:

**Gate Requirements:**
1. ✅ Count ≥ 20 trades - PASS (371 trades)
2. ❌ Profit Factor ≥ 1.25 - FAIL (1.109 < 1.25)
3. ✅ Win Rate ≥ 38% - PASS (38.01%)
4. ❌ Improvement ≥ 10% vs baseline - FAIL (-0.1%)

## Problem Diagnosis

### Issue #1: GDELT Query Too Broad
**Query:** `"gold OR xau OR bullion OR inflation OR yields OR fed OR cpi OR nfp"`

**Problem:** Matches ANY article mentioning these keywords, even tangentially.

**Examples of matched headlines (NOT gold-relevant):**
- "China economy is at the mercy of a force completely beyond its control"
- "Is your income in the top 1% in your state?"
- "Qatar Airways seeks engine guarantees for revamped Airbus order"
- "Ed Sheeran announces title of new album, full track listing"
- "Taylor Swift wants to landmark her storied Beverly Hills estate"

**Solution:** Need stricter query:
- Require "gold" OR "xau" in headline (not just body)
- Add context requirements ("gold AND (price OR rally OR falls)")

### Issue #2: FinBERT Sentiment is Generic
**FinBERT** classifies general financial sentiment (positive/negative/neutral), not gold-specific.

**Problem:** A headline like "Dollar rallies to 2-year high" is classified as:
- FinBERT: Positive (good for dollar)
- Our mapping: Bearish for gold (correct)
- But: Mapping logic only works if headline is about gold/macro

**Most headlines are neutral business news** → FinBERT correctly classifies as neutral → Net sentiment near zero.

### Issue #3: Headline Volume ≠ Gold Relevance
We got 250 headlines per trade window, but:
- Only ~15 mention gold (5.9%)
- Only ~6 mention Fed (2.4%)
- Only ~9 mention inflation (3.8%)

**The other 220 headlines are noise** (general business news, stocks, politics, entertainment).

## Alternative Approaches

### ❌ Abandoned: Sentiment Direction Filter
**Why it failed:**
- Too few gold-relevant headlines
- Sentiment too neutral
- No strong directional signal
- Manual 111 events had 10.5x advantage but only 9 test trades
- GDELT 478K headlines but no advantage

### ✅ Recommended: Hybrid Manual + GDELT Real-Time

**Strategy:**
1. **Keep manual 111 major events** for historical advantage (10.5x pips, 66.7% WR)
2. **Use GDELT for FUTURE trades** in real-time:
   - Query: `"gold" AND ("price" OR "rally" OR "falls" OR "surge")`
   - Require ≥3 gold-specific headlines in 30-min window
   - Use headline COUNT as signal, not sentiment
3. **Combined backtest**:
   - Historical: Manual events (140/2490 trades)
   - Simulate real-time GDELT for remainder
   - Target: 20-30 test trades total

### ✅ Alternative: Volume/Volatility Filter

**Hypothesis:** High headline count = major market event = avoid (too volatile/unpredictable)

**Filter Logic:**
```python
# Avoid trades during major news events
avoid = (df["headline_count"] >= 30) & (df["sentiment_volatility"] > 0.15)
filtered = df[~avoid]  # Trade only when NOT major news
```

**Rationale:**
- News doesn't predict direction
- News causes volatility and slippage
- Better to trade in quiet periods
- Inverse of what we tried (but might work!)

### ✅ Alternative: Refine GDELT Query

**New Query:**
```
("gold price" OR "gold rally" OR "gold falls" OR "xauusd" OR "gold bullion") 
AND NOT ("golden" OR "gold medal" OR "golden state")
```

**Expected:**
- 5K-10K headlines (vs 478K)
- 90%+ gold-relevant (vs 6%)
- Stronger sentiment signal
- Re-run sentiment analysis

## Next Steps (Prioritized)

### Option 1: Accept Baseline (RECOMMENDED)
**Decision:** GDELT sentiment filter doesn't work. Accept baseline PF 1.13.

**Rationale:**
- 5 ML attempts failed
- Manual events too low frequency
- GDELT too noisy
- **Focus on what works**: SuperTrend pattern + EMA200 day filter

**Next:** Move to Phase 4 (Portfolio Management)
- Position sizing based on volatility
- Multi-timeframe confirmation
- Drawdown-based cooldowns
- Multiple instrument diversification

### Option 2: Refine GDELT Query
**Time:** 2-3 hours
**Steps:**
1. Update GDELT query to gold-specific
2. Re-fetch (expect 5K-10K headlines vs 478K)
3. Re-run sentiment analysis
4. Backtest
5. Validate if signal improves

**Risk:** May still fail (sentiment still noisy)

### Option 3: Volume-Based Anti-Filter
**Time:** 30 minutes
**Steps:**
1. Create filter: Avoid trades when headline_count ≥30
2. Backtest
3. Check if avoiding major news improves PF

**Risk:** May not help (news volume might not correlate with bad trades)

### Option 4: Keep Manual Events Only
**Decision:** Abandon GDELT, keep 111 manual events for deployment

**Deployment:**
- Use manual events as "known high-impact times"
- Trade only during these windows
- Accept low frequency (9 test trades)
- Deploy as "high-conviction special situations" strategy

**Pro:** Validated 10.5x advantage
**Con:** Too low frequency for practical trading

## Technical Debt

### Files Created (All Working)
```
✅ sentiments/fetch_news_gdelt.py (enhanced)
✅ scripts/ml/analyze_gdelt_sentiment.py
✅ scripts/ml/backtest_gdelt_filter.py
✅ run_gdelt_pipeline.py
✅ requirements_sentiment.txt
✅ docs/GDELT_SETUP.md
✅ README_GDELT.md
```

### Data Generated
```
✅ sentiments/news/headlines_raw.csv (478K headlines)
✅ data/features/trades_sentiment_gdelt.parquet (2,490 trades × 12 features)
✅ results/ml/gdelt_backtest/filter_performance.csv
✅ results/ml/gdelt_backtest/deployment_gates.csv
```

## Lessons Learned

### ✅ What Worked
1. **News timing matters** - Manual events showed 10.5x advantage
2. **Infrastructure is solid** - GDELT fetcher, FinBERT analyzer work well
3. **Backtest framework** - Proper train/val/test splits, deployment gates

### ❌ What Didn't Work
1. **Generic news queries** - Too much noise (94% irrelevant)
2. **Sentiment classification** - Can't predict gold direction from general news
3. **High volume ≠ high signal** - 478K headlines but no edge

### 🎯 Key Insights
1. **ML cannot predict individual trades** (5 attempts, all failed)
2. **News filter needs to be VERY specific** (only major gold events)
3. **Volume without relevance is useless** (478K headlines, 5.9% relevant)
4. **Low frequency + high edge > High frequency + no edge** (9 trades @ PF 2.6 better than 371 @ PF 1.1)

## Recommendation

**Accept baseline strategy (PF 1.13) and move to Phase 4: Portfolio Management**

**Why:**
- SuperTrend + EMA200 is profitable (PF 1.13-1.19)
- News filters don't improve it
- ML doesn't work
- Better to optimize:
  - Position sizing
  - Risk management
  - Multiple timeframes
  - Multiple instruments
  - Drawdown controls

**OR**

**Refine GDELT query for gold-specific headlines (2-3 hour effort)**
- Last attempt before accepting baseline
- If still fails → move to Phase 4

---

**Current Status:** ✅ Complete analysis, awaiting decision on next steps.
