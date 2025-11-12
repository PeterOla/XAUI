# XAUUSD 1m SuperTrend + News Sentiment Filter

Lean, production-focused strategy for trading XAUUSD using a 1-minute SuperTrend setup plus a combined news sentiment filter. Validated on Jan 2024–Oct 2025.

## Highlights

- Trade window: 13:00–16:00 UTC
- Entry: SuperTrend flip + alternating candle; Exit: cross back through ST (max SL distance capped)
- Filters: Daily EMA200 trend + Combined news sentiment (bearish OR bullish)
- Performance (test): 140 trades, PF 1.355, WR 45.0%, +41.40 pips/trade
- Recommendation: Use COMBINED filter in production

See `docs/VOLUME_ANALYSIS.md` for volume vs quality comparison.

## Data Requirements

Place the following locally (gitignored due to size). If you need access, email: Olalerupeter@gmail.com

- Price: `data/combined_xauusd_1min_full.csv` (UTC, 1m OHLC; columns: timestamp,Open,High,Low,Close)
- Trend: `data/ema200_trend_by_date.csv`
- Clean features: `data/features/trades_sentiment_gold_clean.parquet`
- Clean headlines (optional reference): `sentiments/news/headlines_gold_specific_clean.csv`

## Install

```powershell
pip install -r requirements.txt
# Optional (only if rebuilding sentiment features):
pip install -r requirements_sentiment.txt
```

## Quick Start

Backtest with news filter (combined):
```powershell
python scripts\strategy_with_news_filter.py --use-news-filter --filter-type combined --entry-hours 13-16 --trend up
```

Generate EMA200 trend file (if missing):
```powershell
python scripts\generate_ema200_trend.py --input-csv data\combined_xauusd_1min_full.csv --out-csv data\ema200_trend_by_date.csv
```

## Paper Deploy and Monitor

```powershell
# Start paper deployment
python scripts\deploy_live_strategy.py --mode paper --validate

# Monitor live/paper performance
python scripts\monitor_performance.py --mode paper --plot --export report.html
```

Go live after ≥2 weeks if gates hold (≥20 trades): PF ≥ 1.25, WR ≥ 38%, Max DD ≤ 2,500 pips.

## Optional: Rebuild Sentiment Features

You can refresh news sentiment features (FinBERT + GDELT) with the minimal scripts under `scripts/ml/`:
- `scripts/ml/analyze_gdelt_sentiment.py`
- `scripts/ml/backtest_gdelt_filter.py`
- `scripts/ml/create_gdelt_events.py`
- `scripts/ml/check_news.py`

The strategy itself uses the cleaned parquet in `data/features/` and does not require model downloads at runtime.

## Repository Structure

```
├── data/
│   ├── combined_xauusd_1min_full.csv
│   ├── ema200_trend_by_date.csv
│   └── features/
│       └── trades_sentiment_gold_clean.parquet
├── sentiments/
│   └── news/
│       └── headlines_gold_specific_clean.csv
├── scripts/
│   ├── base_strategy.py
│   ├── strategy_with_news_filter.py
│   ├── generate_ema200_trend.py
│   ├── deploy_live_strategy.py
│   └── monitor_performance.py
├── docs/
│   ├── VOLUME_ANALYSIS.md
│   └── PLAN_SLIM.md
└── plan.md (slim)
```

## Notes

- All times UTC. Pip size: 0.01 USD per pip.
- Prefer stable, reproducible backtests to complexity; re-validate quarterly.
- Original verbose roadmap was removed; see `plan.md` (slim) and `docs/` for essentials.

## Contact

Questions or data access requests: Olalerupeter@gmail.com