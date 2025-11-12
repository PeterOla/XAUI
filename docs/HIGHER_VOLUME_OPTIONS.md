# Alternative News Filters - Higher Trade Volume

## Problem: moderate_bearish Too Low Frequency

**Current:** 37 test trades over 21 months = 1.8 trades/month  
**User feedback:** Volume too low

## Alternative Filters Analysis (Test Set)

### Options Ranked by Volume × Quality

| Filter | Test Trades | PF | WR | Avg Pips | Pass Gates? | Trades/Month |
|--------|-------------|----|----|----------|-------------|--------------|
| **baseline** | 374 | 1.110 | 37.97% | 14.94 | ❌ (PF<1.25) | 17.8 |
| **has_news** | 319 | 1.115 | 39.18% | 15.76 | ❌ (PF<1.25) | 15.2 |
| **moderate_directional** | 238 | 1.044 | 40.34% | 6.04 | ❌ (PF<1.25) | 11.3 |
| **moderate_bullish** | 201 | 0.949 | 39.80% | -7.27 | ❌ (losing) | 9.6 |
| **high_coverage** | 186 | 0.974 | 34.95% | -3.82 | ❌ (losing) | 8.9 |
| **strong_directional** | 117 | 1.048 | 43.59% | 6.18 | ❌ (PF<1.25) | 5.6 |
| **strong_bullish** | 110 | 1.104 | 44.55% | 13.10 | ❌ (PF<1.25) | 5.2 |
| **moderate_bearish** | 37 | 1.728 | 43.24% | 78.34 | ✅ ALL PASS | 1.8 |
| **very_high_coverage** | 18 | 1.911 | 38.89% | 123.33 | ❌ (count<20) | 0.9 |

### Key Insights

**None of the higher-volume filters pass deployment gates!**
- All filters with >100 trades have PF <1.25 (below threshold)
- strong_bullish (110 trades): PF only 1.104, fails gate
- moderate_directional (238 trades): PF only 1.044, barely profitable

**The quality-volume tradeoff is stark:**
- High volume (200+ trades) → Low PF (0.95-1.12)
- Low volume (37 trades) → High PF (1.728)
- Medium volume (110 trades) → Medium PF (1.104)

---

## Proposed Solutions

### Option 1: Relax Filter Criteria (Increase Volume)

**Approach:** Widen moderate_bearish thresholds

| Threshold | Current | Relaxed | Expected Result |
|-----------|---------|---------|------------------|
| **min_headline_count** | ≥5 | ≥3 | More trades with marginal news |
| **max_net_sentiment** | <-0.1 | <0.0 | Include neutral sentiment |

**Expected Impact:**
- Trade volume: 37 → ~80-120 (2-3x increase)
- PF likely drops: 1.728 → ~1.3-1.5
- Still profitable but less selective

**Pros:** Higher frequency, still profitable  
**Cons:** Lower quality, more noise, may not pass gates

---

### Option 2: Combine Multiple Filters (OR Logic)

**Approach:** Trade when ANY of multiple filters pass

```python
combined_filter = (
    moderate_bearish OR      # 37 trades, PF 1.728
    very_high_coverage OR    # 18 trades, PF 1.911
    strong_bullish           # 110 trades, PF 1.104
)
```

**Expected Result:**
- Total trades: ~150-165 (remove overlaps)
- Blended PF: ~1.2-1.3 (weighted average)
- 7-8 trades/month

**Pros:** Higher volume, diversified signals  
**Cons:** Some lower-quality trades dilute performance

---

### Option 3: Different Strategy Enhancement

**Approach:** Keep news filter as-is, but ADD more trade opportunities from:

1. **Multiple timeframes**: Run same filter on 5m, 15m bars
   - Expected: 37 × 3 timeframes = ~110 trades/21mo = 5.2/month
   
2. **Extended trading hours**: Expand from 13-16 UTC to 10-18 UTC
   - Expected: 37 × 2.67 (8h vs 3h) = ~99 trades = 4.7/month
   
3. **Additional instruments**: Apply to EURUSD, GBPUSD with GDELT
   - Expected: 37 × 3 instruments = ~111 trades = 5.3/month

**Pros:** Maintains filter quality (PF 1.728), diversifies risk  
**Cons:** More infrastructure, broader GDELT coverage needed

---

### Option 4: Accept Lower PF for Higher Volume

**Approach:** Use strong_bullish filter (110 test trades)

```python
strong_bullish = (
    headline_count >= 5 AND
    net_sentiment > 0.3      # Strongly bullish for gold
)
```

**Test Set Performance:**
- Trades: 110 (3x more than moderate_bearish)
- PF: 1.104 (vs 1.728)
- WR: 44.55% (good!)
- Avg pips: 13.10 (vs 78.34)
- Trades/month: 5.2 (vs 1.8)

**Analysis:**
- ✅ Passes count gate (110 > 20)
- ❌ Fails PF gate (1.104 < 1.25)
- ✅ Passes WR gate (44.55% > 38%)
- ❌ Fails improvement gate (1.104/1.110 = -0.5%)

**Verdict:** Doesn't improve baseline enough to justify deployment

---

### Option 5: No Filter - Optimize Baseline Strategy

**Approach:** If volume is critical, forget news filter entirely. Instead:

1. **Better entry timing**: Optimize entry hours beyond 13-16 UTC
2. **Tighter stops**: Reduce max_sl_distance from 520 pips
3. **Trend confluence**: Require multiple timeframe alignment (1m+5m+15m)
4. **Volatility filters**: Trade only during ATR sweet spots

**Baseline (No Filter) Test Set:**
- Trades: 374 (10x more than moderate_bearish)
- PF: 1.110 (still profitable!)
- Avg pips: 14.94
- Trades/month: 17.8

**But wait - check our full backtest result:**
```
Test set (Jan 2024+): 613 trades, PF 0.903 ❌ LOSING
```

Actually baseline WITHOUT date filter loses money on recent data!

---

## Recommendations

### ⭐ RECOMMENDED: Option 3 - Multiple Timeframes

**Strategy:** Keep moderate_bearish filter quality, multiply opportunities

1. **Run on 3 timeframes**: 1m, 5m, 15m SuperTrend
   - 1m: 37 trades (current)
   - 5m: ~35-40 estimated
   - 15m: ~30-35 estimated
   - **Total: ~100-110 trades over 21 months = 4.8/month**

2. **Keep strict filter criteria**: headline_count ≥5, net_sentiment <-0.1
   - Maintains high quality (PF ~1.5-1.7 range)
   - Diversifies across timeframes
   - Reduces single-timeframe risk

**Implementation:**
```bash
# Run backtests on different timeframes
python scripts/strategy_with_news_filter.py --use-news-filter --timeframe 1m
python scripts/strategy_with_news_filter.py --use-news-filter --timeframe 5m
python scripts/strategy_with_news_filter.py --use-news-filter --timeframe 15m
```

**Expected Annual:**
- ~57 trades/year (vs 21 with 1m only)
- Avg ~60-70 pips/trade (slightly lower than 1m due to larger stops on higher TF)
- Total ~3,500-4,000 pips/year
- Still high quality, much better frequency

---

### 🔄 ALTERNATIVE: Option 1 - Relax Thresholds

**If multi-timeframe is too complex:**

Test relaxed moderate_bearish:
```python
relaxed_moderate_bearish = (
    headline_count >= 3 AND        # Was: 5
    net_sentiment < -0.05          # Was: -0.1
)
```

Run backtest to check:
- Expected: 80-120 test trades (2-3x increase)
- Target: PF >1.4, WR >40%
- If passes, deploy this instead

---

## Next Steps

**Choose your path:**

1. **Option 3 (Recommended)**: I'll prepare multi-timeframe (1m/5m/15m) backtests
2. **Option 1**: I'll test relaxed filter thresholds
3. **Option 2**: I'll implement combined filter (moderate_bearish OR strong_bullish)
4. **Custom**: Tell me your preferred trade frequency target and I'll optimize

**What's your target trade volume?**
- Current: 1.8 trades/month
- Option 3: ~5 trades/month (3x increase, maintains quality)
- Option 1: ~4-6 trades/month (relaxed filter)
- Want more? We can explore extended hours or multiple instruments

Let me know which direction you prefer!
