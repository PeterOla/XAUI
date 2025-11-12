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
