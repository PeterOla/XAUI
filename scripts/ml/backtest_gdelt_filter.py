#!/usr/bin/env python3
"""
Backtest GDELT news sentiment filter on trading strategy.

This script:
1. Loads trades with GDELT sentiment features
2. Applies various news filters
3. Computes performance metrics by split (train/val/test)
4. Validates deployment gates
5. Compares to baseline (no filter)
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path


def parse_args():
    ap = argparse.ArgumentParser(description="Backtest GDELT sentiment filter")
    ap.add_argument("--features-parquet", type=str, required=True,
                    help="Parquet file with sentiment features")
    ap.add_argument("--out-dir", type=str, default="results/ml/gdelt_backtest",
                    help="Output directory for results")
    ap.add_argument("--test-size", type=float, default=0.15,
                    help="Test set proportion")
    ap.add_argument("--val-size", type=float, default=0.15,
                    help="Validation set proportion")
    return ap.parse_args()


def compute_metrics(df: pd.DataFrame, name: str) -> dict:
    """Compute trading performance metrics."""
    if len(df) == 0:
        return {
            "name": name,
            "count": 0,
            "win_rate": 0.0,
            "avg_pips": 0.0,
            "total_pips": 0.0,
            "profit_factor": 0.0,
            "largest_win": 0.0,
            "largest_loss": 0.0
        }
    
    wins = df[df["pips"] > 0]
    losses = df[df["pips"] <= 0]
    
    win_rate = len(wins) / len(df) * 100
    avg_pips = df["pips"].mean()
    total_pips = df["pips"].sum()
    
    total_wins = wins["pips"].sum() if len(wins) > 0 else 0
    total_losses = abs(losses["pips"].sum()) if len(losses) > 0 else 1
    profit_factor = total_wins / total_losses if total_losses > 0 else 0
    
    largest_win = wins["pips"].max() if len(wins) > 0 else 0
    largest_loss = losses["pips"].min() if len(losses) > 0 else 0
    
    return {
        "name": name,
        "count": len(df),
        "win_rate": round(win_rate, 2),
        "avg_pips": round(avg_pips, 2),
        "total_pips": round(total_pips, 2),
        "profit_factor": round(profit_factor, 3),
        "largest_win": round(largest_win, 2),
        "largest_loss": round(largest_loss, 2)
    }


def apply_filters(df: pd.DataFrame) -> dict:
    """Apply different news filters and return masks."""
    has_headlines = df["headline_count"] >= 5
    strong_bullish = (df["net_sentiment"] > 0.3) & has_headlines
    strong_bearish = (df["net_sentiment"] < -0.3) & has_headlines
    moderate_bullish = (df["net_sentiment"] > 0.1) & has_headlines
    moderate_bearish = (df["net_sentiment"] < -0.1) & has_headlines
    high_coverage = df["headline_count"] >= 10
    very_high_coverage = df["headline_count"] >= 20
    gold_focused = (df["gold_mention_count"] >= 5) & has_headlines
    
    return {
        "baseline": df["headline_count"] >= 0,  # All trades
        "has_news": has_headlines,
        "strong_bullish": strong_bullish,
        "strong_bearish": strong_bearish,
        "strong_directional": strong_bullish | strong_bearish,
        "moderate_bullish": moderate_bullish,
        "moderate_bearish": moderate_bearish,
        "moderate_directional": moderate_bullish | moderate_bearish,
        "high_coverage": high_coverage,
        "very_high_coverage": very_high_coverage,
        "gold_focused": gold_focused
    }


def main():
    args = parse_args()
    
    print("=" * 70)
    print("GDELT Sentiment Filter Backtest")
    print("=" * 70)
    
    # Load data
    print("\n📂 Loading data...")
    df = pd.read_parquet(args.features_parquet)
    print(f"Total trades: {len(df):,}")
    print(f"Date range: {df['entry_time'].min()} to {df['entry_time'].max()}")
    
    # Create train/val/test splits (sequential)
    n = len(df)
    test_start = int(n * (1 - args.test_size))
    val_start = int(n * (1 - args.test_size - args.val_size))
    
    df["split"] = "train"
    df.loc[val_start:test_start-1, "split"] = "val"
    df.loc[test_start:, "split"] = "test"
    
    print(f"\nSplit sizes:")
    print(f"  Train: {(df['split']=='train').sum()} ({(df['split']=='train').sum()/len(df)*100:.1f}%)")
    print(f"  Val:   {(df['split']=='val').sum()} ({(df['split']=='val').sum()/len(df)*100:.1f}%)")
    print(f"  Test:  {(df['split']=='test').sum()} ({(df['split']=='test').sum()/len(df)*100:.1f}%)")
    
    # Apply filters
    filters = apply_filters(df)
    
    # Compute metrics for each split and filter
    results = []
    
    for split in ["train", "val", "test"]:
        split_df = df[df["split"] == split]
        
        for filter_name, filter_mask in filters.items():
            filtered_df = split_df[filter_mask.loc[split_df.index]]
            metrics = compute_metrics(filtered_df, f"{split}_{filter_name}")
            metrics["split"] = split
            metrics["filter"] = filter_name
            results.append(metrics)
    
    results_df = pd.DataFrame(results)
    
    # Save results
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    results_df.to_csv(out_dir / "filter_performance.csv", index=False)
    print(f"\n💾 Saved results to: {out_dir / 'filter_performance.csv'}")
    
    # Print test set results
    print("\n" + "=" * 70)
    print("TEST SET PERFORMANCE")
    print("=" * 70)
    
    test_results = results_df[results_df["split"] == "test"].sort_values("profit_factor", ascending=False)
    
    print("\nTop filters by Profit Factor:")
    print(test_results[["filter", "count", "win_rate", "avg_pips", "profit_factor"]].to_string(index=False))
    
    # Deployment gates
    print("\n" + "=" * 70)
    print("DEPLOYMENT GATES")
    print("=" * 70)
    
    baseline_test = test_results[test_results["filter"] == "baseline"].iloc[0]
    
    gates_results = []
    
    for _, row in test_results.iterrows():
        if row["filter"] == "baseline":
            continue
        
        gate_count = row["count"] >= 20
        gate_pf = row["profit_factor"] >= 1.25
        gate_wr = row["win_rate"] >= 38.0
        gate_improvement = row["profit_factor"] > baseline_test["profit_factor"] * 1.1
        
        all_pass = gate_count and gate_pf and gate_wr and gate_improvement
        
        gates_results.append({
            "filter": row["filter"],
            "count": row["count"],
            "gate_count_pass": "✅" if gate_count else "❌",
            "pf": row["profit_factor"],
            "gate_pf_pass": "✅" if gate_pf else "❌",
            "wr": row["win_rate"],
            "gate_wr_pass": "✅" if gate_wr else "❌",
            "improvement_vs_baseline": f"{(row['profit_factor']/baseline_test['profit_factor']-1)*100:.1f}%",
            "gate_improvement_pass": "✅" if gate_improvement else "❌",
            "all_gates_pass": "✅ DEPLOY" if all_pass else "❌"
        })
    
    gates_df = pd.DataFrame(gates_results)
    gates_df.to_csv(out_dir / "deployment_gates.csv", index=False)
    
    print("\nDeployment Gates (Test Set):")
    print("  1. Count ≥ 20 trades")
    print("  2. Profit Factor ≥ 1.25")
    print("  3. Win Rate ≥ 38%")
    print("  4. Improvement ≥ 10% vs baseline")
    print()
    print(gates_df.to_string(index=False))
    
    # Check if any filter passes all gates
    passing_filters = gates_df[gates_df["all_gates_pass"] == "✅ DEPLOY"]
    
    if len(passing_filters) > 0:
        print("\n" + "🎉" * 35)
        print(f"✅ {len(passing_filters)} FILTER(S) PASS ALL DEPLOYMENT GATES!")
        print("🎉" * 35)
        print("\nRecommended filters for deployment:")
        for _, row in passing_filters.iterrows():
            print(f"  • {row['filter']}")
    else:
        print("\n⚠️ No filters pass all deployment gates.")
        print("Consider relaxing thresholds or combining filters.")
    
    # Save detailed analysis
    print(f"\n💾 Saved deployment gates to: {out_dir / 'deployment_gates.csv'}")
    
    # Print baseline comparison
    print("\n" + "=" * 70)
    print("BASELINE COMPARISON (TEST SET)")
    print("=" * 70)
    
    print(f"\nBaseline (all trades):")
    print(f"  Count: {baseline_test['count']}")
    print(f"  Win Rate: {baseline_test['win_rate']:.2f}%")
    print(f"  Avg Pips: {baseline_test['avg_pips']:.2f}")
    print(f"  Profit Factor: {baseline_test['profit_factor']:.3f}")
    
    best_filter = test_results[test_results["filter"] != "baseline"].iloc[0]
    print(f"\nBest Filter ({best_filter['filter']}):")
    print(f"  Count: {best_filter['count']}")
    print(f"  Win Rate: {best_filter['win_rate']:.2f}% (+{best_filter['win_rate']-baseline_test['win_rate']:.2f}pp)")
    print(f"  Avg Pips: {best_filter['avg_pips']:.2f} ({best_filter['avg_pips']/baseline_test['avg_pips']:.2f}x)")
    print(f"  Profit Factor: {best_filter['profit_factor']:.3f} ({best_filter['profit_factor']/baseline_test['profit_factor']:.2f}x)")


if __name__ == "__main__":
    main()
