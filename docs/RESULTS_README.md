# Results Layout (Slim)

We archived bulky or intermediate result sets to keep the repository lean while preserving the essentials used in our decision-making and deployment.

## Retained (active)
- `results/combined/` — consolidated reports/summaries used for production decisions
- `results/ml/gdelt_clean_backtest/` — final GDELT-based news filter backtest used to validate the combined filter

## Archived
- `results/archive/` contains older baselines, exploratory runs, and large intermediate artifacts:
  - `baseline_*` — legacy trend-only baselines
  - `news_filtered/` — intermediate news-filter runs superseded by the final comparison
  - `trends/` — older per-timeframe outputs
  - `archive/ml/` — ML experiment outputs (features, models, sweeps) not required for production

You can restore any folder by moving it back to its original location. For daily work, use:
- `scripts/strategy_with_news_filter.py` for backtests with the combined filter
- `docs/VOLUME_ANALYSIS.md` for volume vs quality summary
- `docs/PLAN_SLIM.md` and `plan.md` for the concise roadmap
