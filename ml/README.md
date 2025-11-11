# ML Model Registry

This directory contains trained models, metadata, and performance reports for the XAUUSD SuperTrend ML enhancements.

## Directory Structure

```
ml/
├── models/
│   ├── trade_quality_lr.pkl           # Phase 3A: Logistic Regression baseline
│   ├── trade_quality_gbm.pkl          # Phase 3A: LightGBM upgrade
│   ├── day_regime.pkl                 # Phase 3B: Daily regime classifier
│   ├── quantile_sizing.pkl            # Phase 3C: Quantile regression
│   └── metadata/
│       ├── trade_quality_lr_meta.json
│       ├── trade_quality_gbm_meta.json
│       ├── day_regime_meta.json
│       └── quantile_sizing_meta.json
├── reports/
│   ├── trade_quality_metrics_YYYYMMDD.md
│   ├── daily_regime_metrics_YYYYMMDD.md
│   ├── quantile_sizing_metrics_YYYYMMDD.md
│   ├── drift_alert_YYYYMMDD.md
│   └── figures/
│       ├── feature_importance_gbm.csv
│       ├── confusion_matrix_trade_quality.png
│       └── ...
├── feature_sets/
│   ├── feature_schema_trade_quality.json
│   ├── feature_schema_regime.json
│   └── feature_schema_quantile.json
└── logs/
    ├── training_log_YYYYMMDD.json
    └── monitoring_log_YYYYMMDD.json
```

## Models

### Phase 3A: Trade Quality Filter

**Purpose**: Predict whether a candidate trade is high quality before taking it.

**Models**:
- `trade_quality_lr.pkl`: Logistic Regression baseline (interpretable, fast)
- `trade_quality_gbm.pkl`: LightGBM upgrade (better performance)

**Features**:
- Primary: body %, wicks, ATR, EMA distance, up-count, hour, DOW, streak stats
- Secondary (context): Asian range, session flags, breakout indicators

**Label**: `label_win` (1 if pips > 0, else 0)

**Integration**: `--ml-filter ml/models/trade_quality_gbm.pkl --ml-threshold 0.62`

**Acceptance Gates**:
- PF + ≥0.10 vs baseline
- Retain ≥60% trades
- Retain ≥85% top-decile winners

**Status**: ✅ IMPLEMENTED (train_baseline_model.py, threshold_sweep.py)

---

### Phase 3B: Daily Regime Scoring

**Purpose**: Rate each day (Strong / Neutral / Avoid) before trading.

**Model**: `day_regime.pkl` (LightGBM multi-class classifier)

**Features**:
- EMA distance z-scores per TF
- EMA slopes / ATR
- Volatility compression
- Up-count ratio
- Prior 3-day cumulative pips
- Equity curve slope

**Label**: Strong (>75th pct), Neutral (25–75), Avoid (<25 or negative)

**Integration**: `--regime-filter ml/models/day_regime.pkl --regime-threshold 0.55`

**Acceptance Gates**:
- Max DD ≥10% reduction
- PF neutral or improved
- Retain ≥50% trades

**Status**: 🚧 STUB (build_daily_regime_features.py, train_regime_model.py)

---

### Phase 3C: Quantile Sizing

**Purpose**: Dynamic position sizing based on predicted upside/downside.

**Model**: `quantile_sizing.pkl` (LightGBM quantile regression)

**Features**: Extended from Phase 3A (add time-since-flip, ATR trend)

**Predictions**: Q20 (downside), Q50 (median), Q80 (upside)

**Sizing map**:
- score = Q50 / |Q20|
- score < 0.8 → 0.5x
- 0.8–1.2 → 1.0x
- >1.2 → 1.3x (cap)

**Integration**: `--quantile-model ml/models/quantile_sizing.pkl --sizing-enabled`

**Acceptance Gates**:
- Sharpe ≥ +15%
- Max DD not worse
- Worst trade not larger

**Status**: 🚧 STUB (train_quantile_model.py)

---

## Metadata Schema

Each model has a companion `*_meta.json` with:
```json
{
  "model_name": "trade_quality_gbm",
  "model_type": "LightGBM Classifier",
  "training_date": "2025-11-10T14:30:00",
  "features_used": ["body_pct", "ema_dist_atr", ...],
  "label": "label_win (pips > 0)",
  "train_rows": 463,
  "val_rows": 99,
  "test_rows": 99,
  "hyperparameters": {...},
  "val_metrics": {"auc": 0.68, ...},
  "test_metrics": {"auc": 0.65, ...},
  "chosen_threshold": 0.62,
  "pf_improvement_vs_baseline": 0.12,
  "retention_pct": 67,
  "outlier_retention_pct": 88,
  "feature_importance_top5": [...]
}
```

---

## Monitoring & Drift

**Script**: `scripts/ml/monitor_ml.py`

**Checks**:
- Rolling PF, Sharpe, retention %
- Probability compression (std < 0.15)
- Over-filtering (retention < 40%)
- PF drop > 15% vs baseline

**Outputs**: `ml/reports/drift_alert_YYYYMMDD.md`

**Failsafe**: Auto-disable ML if drift persists 2 consecutive weeks.

---

## Changelog

| Date       | Model              | Version | Change Summary                     |
|------------|--------------------|---------|-------------------------------------|
| 2025-11-10 | trade_quality_lr   | v1      | Initial Logistic Regression baseline |
| 2025-11-10 | trade_quality_gbm  | v1      | Initial LightGBM upgrade            |
| TBD        | day_regime         | v1      | Daily regime classifier (planned)   |
| TBD        | quantile_sizing    | v1      | Quantile sizing model (planned)     |

---

## Usage

### Training
```powershell
# Phase 3A: Extract features + train models
python scripts\ml\extract_features.py
python scripts\ml\evaluate_features.py
python scripts\ml\train_baseline_model.py
python scripts\ml\threshold_sweep.py

# Phase 3B: Daily regime (stub)
python scripts\ml\build_daily_regime_features.py
python scripts\ml\train_regime_model.py

# Phase 3C: Quantile sizing (stub)
python scripts\ml\train_quantile_model.py
```

### Integration into strategy
```powershell
# Enable trade quality gating
python scripts\base_strategy.py --ml-filter ml\models\trade_quality_gbm.pkl --ml-threshold 0.62

# Enable regime gating (once implemented)
python scripts\base_strategy.py --regime-filter ml\models\day_regime.pkl --regime-threshold 0.55

# Enable quantile sizing (once implemented)
python scripts\base_strategy.py --quantile-model ml\models\quantile_sizing.pkl --sizing-enabled

# Emergency bypass
python scripts\base_strategy.py --disable-ml
```

### Monitoring
```powershell
python scripts\ml\monitor_ml.py
```

---

## Notes

- All splits are strictly time-forward (no shuffle).
- No feature may use future info relative to trade entry or day start.
- Models default off; require explicit flags to enable.
- Metadata + feature schemas ensure reproducibility.
- Regularly archive models + reports for audit trail.

---

## Contact / Issues

See `plan.md` for acceptance gates and project roadmap.
