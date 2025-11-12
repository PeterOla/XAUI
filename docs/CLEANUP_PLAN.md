# Codebase Cleanup Plan

## Current State Assessment

### Scripts Directory (12 files + ml/)
**Core Production Files (KEEP):**
1. ✅ `strategy_with_news_filter.py` - Main strategy with combined filter
2. ✅ `base_strategy.py` - Base SuperTrend logic
3. ✅ `deploy_live_strategy.py` - Deployment & monitoring setup
4. ✅ `monitor_performance.py` - Performance dashboard
5. ✅ `generate_ema200_trend.py` - EMA200 trend generation

**Analysis/Research (KEEP):**
6. ✅ `analyze_trade_distribution.py` - Trade analysis
7. ✅ `aggregate_results.py` - Results aggregation

**Potentially Remove:**
8. ❓ `run_trend_combinations.py` - Old combination testing
9. ❓ `analyze_sides.py` - Old side analysis
10. ❓ `check_data_range.py` - One-time utility
11. ❓ `check_trend_files.py` - One-time utility

---

### scripts/ml/ Directory (21 files)

**Core News Processing (KEEP):**
1. ✅ `analyze_gdelt_sentiment.py` - Generate sentiment features (CRITICAL!)
2. ✅ `backtest_gdelt_filter.py` - Test news filters
3. ✅ `create_gdelt_events.py` - GDELT data fetching

**Failed ML Experiments (REMOVE):**
4. ❌ `train_baseline_model.py` - Failed ML approach
5. ❌ `train_quantile_model.py` - Failed ML approach
6. ❌ `train_regime_model.py` - Failed ML approach
7. ❌ `extract_features.py` - Old version
8. ❌ `extract_features_v2.py` - Old version
9. ❌ `extract_features_v3.py` - Old version
10. ❌ `merge_features_news.py` - Old merging
11. ❌ `merge_features_v2.py` - Old merging
12. ❌ `build_daily_regime_features.py` - Regime features (failed)
13. ❌ `evaluate_features.py` - Feature evaluation (not used)
14. ❌ `diagnose_proba.py` - Debugging script
15. ❌ `threshold_sweep.py` - Hyperparameter tuning (not needed)
16. ❌ `monitor_ml.py` - ML monitoring (no ML in production)
17. ❌ `ablation_study.py` - Feature ablation (not needed)

**Utilities (MAYBE KEEP):**
18. ❓ `backtest_news_filter.py` - Alternative backtest script
19. ❓ `extract_news_sentiment.py` - Manual news extraction
20. ❓ `check_news.py` - News data checker
21. ❓ `check_merged.py` - Merged data checker

---

## Data Directory

### Keep (Essential):
1. ✅ `data/combined_xauusd_1min_full.csv` - Price data (CRITICAL!)
2. ✅ `data/ema200_trend_by_date.csv` - Trend filter
3. ✅ `sentiments/news/headlines_gold_specific_clean.csv` - Clean news (CRITICAL!)
4. ✅ `data/features/trades_sentiment_gold_clean.parquet` - Final features (CRITICAL!)

### Remove (Intermediate/Old):
- ❌ Old headline versions (headlines_gold_specific.csv with bias)
- ❌ Intermediate parquet files from failed ML attempts
- ❌ Old feature extraction outputs
- ❌ Temporary test files

---

## Results Directory

### Keep:
1. ✅ `results/combined/` - Final combined filter tests
2. ✅ `results/ml/gdelt_clean_backtest/` - Clean data validation
3. ✅ `results/news_filtered/` - News filter results

### Archive or Remove:
- ❌ `results/ml/` (except gdelt_clean_backtest) - Failed ML experiments
- ❌ Old baseline runs
- ❌ Redundant test runs
- ❌ Intermediate matrix results

---

## Documentation

### Keep & Update:
1. ✅ `plan.md` - SLIM DOWN to ~100 lines
2. ✅ `README.md` - UPDATE with current state
3. ✅ `docs/DEPLOYMENT_GUIDE.md` - Production deployment
4. ✅ `docs/FINAL_FILTER_COMPARISON.md` - Strategy comparison
5. ✅ `docs/STRATEGY_COMPARISON.md` - 1m vs 15m comparison
6. ✅ `docs/VOLUME_ANALYSIS.md` - Volume analysis

### Consider Removing:
- ❌ `docs/CLEAN_DATA_RESULTS.md` - Merge into main docs
- ❌ `docs/HIGHER_VOLUME_OPTIONS.md` - Outdated (pre-combined filter)

---

## Cleanup Actions

### Phase 1: Remove Failed ML Code (Priority 1)
```bash
# Remove failed ML training scripts
rm scripts/ml/train_*.py
rm scripts/ml/extract_features*.py
rm scripts/ml/merge_features*.py
rm scripts/ml/build_daily_regime_features.py
rm scripts/ml/evaluate_features.py
rm scripts/ml/diagnose_proba.py
rm scripts/ml/threshold_sweep.py
rm scripts/ml/monitor_ml.py
rm scripts/ml/ablation_study.py
```

**Result:** 13 files removed, keep only 8 core files

### Phase 2: Clean Old Utilities
```bash
# Remove one-time utility scripts
rm scripts/run_trend_combinations.py
rm scripts/analyze_sides.py
rm scripts/check_data_range.py
rm scripts/check_trend_files.py
```

**Result:** 4 files removed

### Phase 3: Organize ML Directory
**Keep only:**
- `analyze_gdelt_sentiment.py` (sentiment generation)
- `backtest_gdelt_filter.py` (filter validation)
- `create_gdelt_events.py` (data fetching)
- `check_news.py` (data validation)

**Total:** 4 files (down from 21!)

### Phase 4: Data Cleanup
```bash
# Remove old/biased headlines
rm sentiments/news/headlines_gold_specific.csv  # Old version with bias

# Remove intermediate ML features
rm -rf data/features/*ml*.parquet
rm -rf data/features/*regime*.parquet
rm -rf data/features/*quantile*.parquet

# Keep only:
# - trades_sentiment_gold_clean.parquet
```

### Phase 5: Results Archive
```bash
# Create archive directory
mkdir -p archive/old_ml_experiments
mkdir -p archive/old_baselines

# Move failed ML results
mv results/ml/* archive/old_ml_experiments/ (except gdelt_clean_backtest)

# Keep only production results
```

### Phase 6: Slim Down plan.md
**From 350+ lines → ~100 lines**

Focus on:
- Current validated strategy (combined filter)
- Key metrics (PF 1.355, WR 45%, 6.7 trades/month)
- Deployment status
- Phase 4 goals (ML entry system)

Remove:
- Detailed Phase 3A journey (move to docs/)
- Monthly breakdowns
- Excessive historical detail

---

## Final Structure

```
XAUI/
├── data/
│   ├── combined_xauusd_1min_full.csv          ✅ Price data
│   ├── ema200_trend_by_date.csv               ✅ Trend filter
│   └── features/
│       └── trades_sentiment_gold_clean.parquet ✅ Final features
│
├── sentiments/
│   └── news/
│       └── headlines_gold_specific_clean.csv   ✅ Clean news
│
├── scripts/
│   ├── base_strategy.py                        ✅ Core logic
│   ├── strategy_with_news_filter.py            ✅ Main strategy
│   ├── deploy_live_strategy.py                 ✅ Deployment
│   ├── monitor_performance.py                  ✅ Monitoring
│   ├── generate_ema200_trend.py                ✅ Trend gen
│   ├── analyze_trade_distribution.py           ✅ Analysis
│   ├── aggregate_results.py                    ✅ Aggregation
│   └── ml/
│       ├── analyze_gdelt_sentiment.py          ✅ Sentiment gen
│       ├── backtest_gdelt_filter.py            ✅ Filter test
│       ├── create_gdelt_events.py              ✅ Data fetch
│       └── check_news.py                       ✅ Validation
│
├── results/
│   ├── combined/                               ✅ Final results
│   ├── ml/gdelt_clean_backtest/                ✅ Clean validation
│   └── news_filtered/                          ✅ News results
│
├── docs/
│   ├── DEPLOYMENT_GUIDE.md                     ✅ How to deploy
│   ├── FINAL_FILTER_COMPARISON.md              ✅ All filters
│   ├── STRATEGY_COMPARISON.md                  ✅ 1m vs 15m
│   └── VOLUME_ANALYSIS.md                      ✅ Volume study
│
├── plan.md                                     ✅ Slimmed down
└── README.md                                   ✅ Updated
```

**Before:** 64+ scripts, 350+ line plan, cluttered data  
**After:** 11 core scripts, ~100 line plan, clean structure

---

## Execution Order

1. ✅ Audit complete (this document)
2. ⏳ Remove failed ML scripts (13 files)
3. ⏳ Remove old utilities (4 files)
4. ⏳ Clean data directory
5. ⏳ Slim down plan.md (350→100 lines)
6. ⏳ Update README.md
7. ⏳ Archive old results

**Ready to execute cleanup?**
