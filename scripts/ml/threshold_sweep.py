"""
Threshold sweep: for each model probability cutoff, compute retained PF, trade count, outlier retention.
Phase 3A calibration to find optimal operating point.
"""
import argparse
import os
import pickle
import json
from pathlib import Path
import pandas as pd
import numpy as np

def profit_factor(pips: pd.Series):
    gains = pips[pips > 0].sum()
    losses = pips[pips < 0].sum()
    return float(gains / abs(losses)) if losses < 0 else np.inf

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=os.path.join("ml","models","trade_quality_gbm.pkl"))
    ap.add_argument("--features-parquet", default=os.path.join("data","features","trades_features.parquet"))
    ap.add_argument("--split-indices", default=os.path.join("data","features","splits","test_indices.csv"))
    ap.add_argument("--out-csv", default=os.path.join("results","ml","threshold_sweep_results.csv"))
    ap.add_argument("--min-threshold", type=float, default=0.50)
    ap.add_argument("--max-threshold", type=float, default=0.80)
    ap.add_argument("--step", type=float, default=0.02)
    args = ap.parse_args()

    Path(os.path.dirname(args.out_csv)).mkdir(parents=True, exist_ok=True)

    # Load model and metadata
    with open(args.model, "rb") as f:
        model = pickle.load(f)
    
    # Load metadata to get exact feature list
    meta_path = args.model.replace(".pkl", "_meta.json").replace("models", "models/metadata")
    with open(meta_path, "r") as f:
        meta = json.load(f)
    feature_cols = meta["features_used"]

    # Load features
    df = pd.read_parquet(args.features_parquet)
    test_idx = pd.read_csv(args.split_indices)["entry_bar"]
    test_idx = pd.to_datetime(test_idx)
    test = df.loc[test_idx]

    # Use exact features from training, apply same imputation
    X_test = test[feature_cols].fillna(test[feature_cols].median()).fillna(0)
    y_test = test["label_win"].astype(int)
    pips_test = test["pips"]

    # Predict
    proba = model.predict_proba(X_test)[:,1]

    # Baseline PF (all trades)
    baseline_pf = profit_factor(pips_test)
    baseline_total = len(test)

    # Top decile trades (by pips) for outlier retention
    top_decile_threshold = pips_test.quantile(0.90)
    top_decile_mask = pips_test >= top_decile_threshold
    top_decile_count = top_decile_mask.sum()

    # Sweep
    results = []
    thresholds = np.arange(args.min_threshold, args.max_threshold + args.step, args.step)
    for t in thresholds:
        mask = proba >= t
        retained = test[mask]
        if len(retained) == 0:
            results.append({
                "threshold": float(t),
                "retained_count": 0,
                "retained_pct": 0.0,
                "pf": np.nan,
                "total_pips": 0.0,
                "outlier_retention_pct": 0.0,
            })
            continue
        ret_pips = retained["pips"]
        ret_pf = profit_factor(ret_pips)
        outlier_retained = (top_decile_mask & mask).sum()
        results.append({
            "threshold": float(t),
            "retained_count": len(retained),
            "retained_pct": float(len(retained) / baseline_total * 100),
            "pf": float(ret_pf) if np.isfinite(ret_pf) else np.nan,
            "total_pips": float(ret_pips.sum()),
            "outlier_retention_pct": float(outlier_retained / top_decile_count * 100) if top_decile_count > 0 else 0.0,
        })

    sweep_df = pd.DataFrame(results)
    sweep_df.to_csv(args.out_csv, index=False)

    print(f"✅ Threshold sweep complete: {args.out_csv}")
    print(f"   Baseline PF: {baseline_pf:.2f} | Trades: {baseline_total}")
    print(f"   Sweep range: {args.min_threshold}–{args.max_threshold} (step {args.step})")
    print(sweep_df.head(10))

if __name__ == "__main__":
    main()
