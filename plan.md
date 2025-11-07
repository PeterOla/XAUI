# XAUI Project Plan

This plan outlines immediate execution steps, near-term research improvements, and medium-term ML enhancements for the XAUUSD SuperTrend strategy.

## Phase 1 — Baseline Run (Default: up_buy_only)

Goal: Establish a consistent, reproducible baseline using the full dataset, trading only on Up-trend days and taking Long entries only ("up_buy_only").

- Defaults set in `scripts/base_strategy.py`:
  - Input CSV default: `C:\\Users\\Olale\\Documents\\Codebase\\Quant\\XAUI\\data\\twelvedata_xauusd_1min_full.csv` with fallback to `data/twelvedata_xauusd_1min_full.csv` and `data/combined_xauusd_1min_full.csv`.
  - Trend filter default: `up` (uses `data/ema200_trend_by_date.csv` if present; otherwise no default filter).
  - Side default: `long-only` when no side flags are provided.
  - Auto run-tag when defaults imply Up + Long-only: `up_buy_only`.

Run (after placing data files):
```powershell
# Optional: quick smoke test
python scripts/base_strategy.py --max-rows 200 --plot

# Full run (uses defaults)
python scripts/base_strategy.py --plot
```

Artifacts:
- Results CSVs in `results/`
- Plot in `results/`
- Console summary and performance metrics

Acceptance:
- Reproduce metrics similar to prior `up_buy_only` summary (see results/combined/up_buy_only/summary.txt).
- Verify no exceptions and sensible trade counts.

## Phase 2 — Multi-Timeframe Trend Filters (Completed Core, Pending Extensions)

Objective: Improve selectivity by incorporating EMA200-based regime filters from higher timeframes and combinations.

Implemented:
- Multi-timeframe EMA200 daily trend generation (`scripts/generate_ema200_trend.py`) for 1m,5m,15m,30m,1h,4h using per-timeframe cutoff times (pre overlap) — DONE.
- Combination runs requiring ALL selected timeframes Up via `--trend-tfs` in `base_strategy.py` — DONE.
- Aggregation of performance across single TFs and combo folders (`scripts/aggregate_results.py`) — DONE.

Pending / Enhancements:
- Introduce K-of-N confirmation (at least K Up timeframes out of N) instead of strict ALL — PLANNED.
- Provide ANY rule (≥1 Up) mainly for diagnostic comparison — OPTIONAL.
- Parameterize cutoff times externally (config file) for reproducible regime definitions — PLANNED.

Targets (initial + extended):
- Single-TF filters: 5m, 15m, 30m, 1h, 4h — DONE.
- Strict multi-TF (ALL): examples (1m+5m+15m), (full 6-pack) — DONE.
- K-of-N dynamic (e.g., majority vote) — PLANNED.

Success criteria:
- Equal or better PF vs baseline while reducing drawdown clusters.
- K-of-N should retain ≥60% of trades vs ALL while improving PF or Sharpe.

Metrics to track additionally:
- PF and Max DD by Up-count bucket (number of timeframes Up) — PLANNED.
- Trade expectancy drift when tightening K — PLANNED.

## Phase 3 — Machine Learning Enhancements (Roadmap)

Objective: Lift PF and Sharpe by filtering or sizing trades using predictive models.

Approach 1: Meta-Label Trade Quality Filter (Phase 3A)
- Build `scripts/extract_features.py` to join trade outcomes with pre-entry features.
- Features: candle anatomy (body %, wick %), ATR(14), distance to SuperTrend & EMA200 (raw and %), multi-TF Up count, recent streak stats, hour-of-day, day-of-week, initial stop size.
- Model: Logistic Regression (baseline) → LightGBM (upgrade).
- Output: probability of high-quality trade (win or > threshold pips).
- Integration: `--ml-filter model.pkl --ml-threshold 0.6` inside `base_strategy.py`.
- Success: retain ≥60% trades, PF +0.10 absolute, drawdown ≤ baseline -10%.

Approach 2: Daily Regime Confidence (Phase 3B)
- Features aggregated per day: EMA distance z-scores per TF, slopes, volatility compression (range / median range), Up-count ratio, prior 3–5 day net pips, equity slope.
- Model: Regression or classification producing regime score.
- Use score to gate trading days or modulate position size tier (Strong / Neutral / Avoid).

Approach 3: Quantile / Distribution Forecast for Dynamic Sizing (Phase 3C)
- Predict expected pips plus lower/upper quantiles (e.g. 20% / 80%).
- Position size multiplier = f(ExpectedGain / |LowerTail|).
- Libraries: LightGBM quantile mode or NGBoost.
- Success: Sharpe uplift >15%, tail losses controlled (VaR not worse than baseline).

General ML Practices
- Time-based validation splits (no random shuffle) to avoid leakage.
- Feature pipeline object saved alongside model (versioned under `ml/` directory).
- Metrics: ROC-AUC, Precision@TopDecile, lift curve, PF/Sharpe comparison, retained outlier count.

Milestone Checklist
1. (3A) Feature extraction & dataset creation — PENDING.
2. (3A) Baseline classifier & threshold calibration — PENDING.
3. (3A) Integrate gating CLI & log accepted/rejected stats — PENDING.
4. (3B) Daily regime feature builder & scoring model — PENDING.
5. (3B) Day-level gating / size tier integration — PENDING.
6. (3C) Quantile model & dynamic sizing logic — PENDING.
7. Monitoring script for live acceptance rate & performance drift — PENDING.

Risk Controls to Add
- Max consecutive rejected trades trigger threshold re-check.
- Adaptive threshold (optimize weekly on recent validation window).
- Failsafe: if model confidence distribution collapses (e.g., all ~0.5), revert to pure rules.

Data Artifacts
- `data/features/trades_features.parquet` (feature store).
- `ml/models/trade_quality_v1.pkl`.
- `ml/models/day_regime_v1.pkl`.
- `ml/reports/metrics_<date>.md`.

## Phase 4 — Position Sizing & Risk Layer (Future)
- Implement dynamic position scaling (quantile model output) — FUTURE.
- Add equity curve based cooldown logic (pause after DD threshold) — FUTURE.
- Optional ensemble (vote of regime score + trade classifier) — FUTURE.

## Completed Summary (Snapshot)
- Baseline strategy run & artifacts validated.
- Multi-timeframe EMA trend generation (1m–4h) with per-TF cutoff times.
- Combination ALL logic via `--trend-tfs`.
- Aggregator for single & combo timeframes.
- Plot performance optimization (--plot-lite, --plot-latest-only).
- Date-range filtering, output directory structure, combo result folders.
- Noon-open experiment evaluated and reverted (PF impact understood).

## Next Actions (Updated)
- [ ] Implement K-of-N confirmation: add `--trend-tfs` plus `--trend-min-k` to relax strict ALL.
- [ ] Add Up-count bucket metrics in aggregator (PF per count bucket).
- [ ] Build feature extraction script (Phase 3A).
- [ ] Train baseline trade quality classifier & integrate `--ml-filter` gating.
- [ ] Log accepted/rejected trade performance for calibration.
- [ ] Implement daily regime scoring (Phase 3B) & integrate optional day gating.
- [ ] Design quantile sizing prototype (Phase 3C) behind experimental flag.
- [ ] Add monitoring report generator for weekly model performance.
- [ ] Version ML artifacts under `ml/` with README.

## Acceptance Gates (For ML Integration)
- Meta-label filter: PF + ≥0.10 absolute vs baseline, trade retention ≥60%, outlier retention ≥85%.
- Regime score: Max DD reduction ≥10% with neutral PF or PF improvement.
- Quantile sizing: Sharpe improvement ≥15%; no increase in worst trade magnitude.

## Change Log Notes
- Updated plan to reflect completed trend filter work and detailed ML roadmap.
- Added K-of-N confirmation as strategic enhancement prior to ML gating.
