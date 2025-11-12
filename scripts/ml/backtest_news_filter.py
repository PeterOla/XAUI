"""
Backtest news-only filter: Trade only within 3 hours of major events.

Validates if the 7.1x pips advantage observed in news trades holds up
in proper train/val/test splits with same temporal ordering as ML experiments.
"""
import argparse
import pandas as pd
import numpy as np
from pathlib import Path


def compute_metrics(trades_df):
    """Compute performance metrics for a set of trades."""
    if len(trades_df) == 0:
        return {
            "count": 0,
            "win_rate": 0,
            "avg_pips": 0,
            "total_pips": 0,
            "profit_factor": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "largest_win": 0,
            "largest_loss": 0,
        }
    
    wins = trades_df[trades_df["pips"] > 0]
    losses = trades_df[trades_df["pips"] <= 0]
    
    win_pips = wins["pips"].sum() if len(wins) > 0 else 0
    loss_pips = abs(losses["pips"].sum()) if len(losses) > 0 else 0
    
    return {
        "count": len(trades_df),
        "win_rate": len(wins) / len(trades_df) * 100,
        "avg_pips": trades_df["pips"].mean(),
        "total_pips": trades_df["pips"].sum(),
        "profit_factor": win_pips / loss_pips if loss_pips > 0 else (win_pips if win_pips > 0 else 0),
        "avg_win": wins["pips"].mean() if len(wins) > 0 else 0,
        "avg_loss": losses["pips"].mean() if len(losses) > 0 else 0,
        "largest_win": wins["pips"].max() if len(wins) > 0 else 0,
        "largest_loss": losses["pips"].min() if len(losses) > 0 else 0,
    }


def print_metrics(name, metrics, indent=0):
    """Pretty print metrics."""
    prefix = "  " * indent
    print(f"\n{prefix}{'='*60}")
    print(f"{prefix}{name}")
    print(f"{prefix}{'='*60}")
    print(f"{prefix}Trades:        {metrics['count']:,}")
    print(f"{prefix}Win Rate:      {metrics['win_rate']:.2f}%")
    print(f"{prefix}Avg Pips:      {metrics['avg_pips']:.2f}")
    print(f"{prefix}Total Pips:    {metrics['total_pips']:.1f}")
    print(f"{prefix}Profit Factor: {metrics['profit_factor']:.3f}")
    print(f"{prefix}Avg Win:       {metrics['avg_win']:.2f} pips")
    print(f"{prefix}Avg Loss:      {metrics['avg_loss']:.2f} pips")
    print(f"{prefix}Largest Win:   {metrics['largest_win']:.1f} pips")
    print(f"{prefix}Largest Loss:  {metrics['largest_loss']:.1f} pips")


def main():
    parser = argparse.ArgumentParser(description="Backtest news-only filter")
    parser.add_argument(
        "--features-parquet",
        default="data/features/trades_features_2490_v3_with_news_v2.parquet",
        help="Features parquet with has_event_nearby column"
    )
    parser.add_argument(
        "--out-dir",
        default="results/ml/news_filter_backtest",
        help="Output directory for results"
    )
    args = parser.parse_args()
    
    # Load features
    print("Loading features...")
    df = pd.read_parquet(args.features_parquet)
    print(f"Total trades: {len(df):,}")
    print(f"Trades with nearby events: {df['has_event_nearby'].sum()}")
    
    # Sequential time split (same as ML experiments: 70/15/15)
    n = len(df)
    train_end = int(0.70 * n)
    val_end = int(0.85 * n)
    
    df_train = df.iloc[:train_end].copy()
    df_val = df.iloc[train_end:val_end].copy()
    df_test = df.iloc[val_end:].copy()
    
    print(f"\nSplits: Train={len(df_train)} | Val={len(df_val)} | Test={len(df_test)}")
    
    # Split by news filter
    train_news = df_train[df_train["has_event_nearby"] == 1]
    train_no_news = df_train[df_train["has_event_nearby"] == 0]
    
    val_news = df_val[df_val["has_event_nearby"] == 1]
    val_no_news = df_val[df_val["has_event_nearby"] == 0]
    
    test_news = df_test[df_test["has_event_nearby"] == 1]
    test_no_news = df_test[df_test["has_event_nearby"] == 0]
    
    print(f"\nTrain: {len(train_news)} news / {len(train_no_news)} no-news")
    print(f"Val:   {len(val_news)} news / {len(val_no_news)} no-news")
    print(f"Test:  {len(test_news)} news / {len(test_no_news)} no-news")
    
    # Compute metrics for each split and filter
    results = {}
    
    # TRAIN
    print("\n" + "="*80)
    print("TRAIN SET ANALYSIS")
    print("="*80)
    
    train_all_metrics = compute_metrics(df_train)
    train_news_metrics = compute_metrics(train_news)
    train_no_news_metrics = compute_metrics(train_no_news)
    
    print_metrics("All Trades (Baseline)", train_all_metrics)
    print_metrics("News Trades Only", train_news_metrics)
    print_metrics("No-News Trades", train_no_news_metrics)
    
    results["train"] = {
        "all": train_all_metrics,
        "news": train_news_metrics,
        "no_news": train_no_news_metrics,
    }
    
    # VALIDATION
    print("\n" + "="*80)
    print("VALIDATION SET ANALYSIS")
    print("="*80)
    
    val_all_metrics = compute_metrics(df_val)
    val_news_metrics = compute_metrics(val_news)
    val_no_news_metrics = compute_metrics(val_no_news)
    
    print_metrics("All Trades (Baseline)", val_all_metrics)
    print_metrics("News Trades Only", val_news_metrics)
    print_metrics("No-News Trades", val_no_news_metrics)
    
    results["val"] = {
        "all": val_all_metrics,
        "news": val_news_metrics,
        "no_news": val_no_news_metrics,
    }
    
    # TEST (CRITICAL - OUT OF SAMPLE)
    print("\n" + "="*80)
    print("TEST SET ANALYSIS (OUT-OF-SAMPLE)")
    print("="*80)
    
    test_all_metrics = compute_metrics(df_test)
    test_news_metrics = compute_metrics(test_news)
    test_no_news_metrics = compute_metrics(test_no_news)
    
    print_metrics("All Trades (Baseline)", test_all_metrics)
    print_metrics("News Trades Only", test_news_metrics)
    print_metrics("No-News Trades", test_no_news_metrics)
    
    results["test"] = {
        "all": test_all_metrics,
        "news": test_news_metrics,
        "no_news": test_no_news_metrics,
    }
    
    # SUMMARY COMPARISON
    print("\n" + "="*80)
    print("FILTER PERFORMANCE SUMMARY")
    print("="*80)
    
    for split_name, split_data in [("Train", results["train"]), 
                                     ("Val", results["val"]), 
                                     ("Test", results["test"])]:
        print(f"\n{split_name}:")
        print(f"  Baseline:     {split_data['all']['count']:4} trades | "
              f"WR {split_data['all']['win_rate']:5.2f}% | "
              f"Avg {split_data['all']['avg_pips']:6.2f} pips | "
              f"PF {split_data['all']['profit_factor']:.3f}")
        
        print(f"  News Only:    {split_data['news']['count']:4} trades | "
              f"WR {split_data['news']['win_rate']:5.2f}% | "
              f"Avg {split_data['news']['avg_pips']:6.2f} pips | "
              f"PF {split_data['news']['profit_factor']:.3f}")
        
        if split_data['news']['count'] > 0 and split_data['all']['avg_pips'] != 0:
            pips_multiplier = split_data['news']['avg_pips'] / split_data['all']['avg_pips']
            wr_diff = split_data['news']['win_rate'] - split_data['all']['win_rate']
            print(f"  → News Advantage: {pips_multiplier:.2f}x pips, {wr_diff:+.2f}pp WR")
    
    # KEY DECISION METRICS
    print("\n" + "="*80)
    print("NEWS FILTER DECISION METRICS (Test Set)")
    print("="*80)
    
    test_news_pf = test_news_metrics["profit_factor"]
    test_baseline_pf = test_all_metrics["profit_factor"]
    test_news_count = test_news_metrics["count"]
    test_news_wr = test_news_metrics["win_rate"]
    
    print(f"\n✓ Trades kept:         {test_news_count} / {test_all_metrics['count']} ({test_news_count/test_all_metrics['count']*100:.1f}%)")
    print(f"✓ Profit Factor:       {test_news_pf:.3f} (vs {test_baseline_pf:.3f} baseline)")
    print(f"✓ Win Rate:            {test_news_wr:.2f}% (vs {test_all_metrics['win_rate']:.2f}% baseline)")
    print(f"✓ Avg Pips:            {test_news_metrics['avg_pips']:.2f} (vs {test_all_metrics['avg_pips']:.2f} baseline)")
    
    # GATES
    print("\n" + "="*80)
    print("DEPLOYMENT GATES")
    print("="*80)
    
    gate_pf = test_news_pf >= 1.25
    gate_wr = test_news_wr >= 38.0
    gate_count = test_news_count >= 15
    gate_improvement = test_news_pf > test_baseline_pf * 1.05
    
    print(f"\n1. Test PF ≥ 1.25:              {'✅ PASS' if gate_pf else '❌ FAIL'} ({test_news_pf:.3f})")
    print(f"2. Test WR ≥ 38%:               {'✅ PASS' if gate_wr else '❌ FAIL'} ({test_news_wr:.2f}%)")
    print(f"3. Test trades ≥ 15:            {'✅ PASS' if gate_count else '❌ FAIL'} ({test_news_count})")
    print(f"4. PF improvement ≥ 5%:         {'✅ PASS' if gate_improvement else '❌ FAIL'} ({test_news_pf/test_baseline_pf:.2f}x)")
    
    all_pass = gate_pf and gate_wr and gate_count and gate_improvement
    
    print(f"\n{'='*80}")
    if all_pass:
        print("✅ ALL GATES PASSED - NEWS FILTER READY FOR DEPLOYMENT")
    else:
        print("❌ GATES FAILED - NEWS FILTER NOT VIABLE")
    print("="*80)
    
    # Save detailed results
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Save summary CSV
    summary_rows = []
    for split_name in ["train", "val", "test"]:
        for filter_type in ["all", "news", "no_news"]:
            metrics = results[split_name][filter_type]
            summary_rows.append({
                "split": split_name,
                "filter": filter_type,
                **metrics
            })
    
    summary_df = pd.DataFrame(summary_rows)
    summary_path = out_dir / "news_filter_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    print(f"\n✅ Summary saved: {summary_path}")
    
    # Save test set trades with filter flag
    test_with_filter = df_test.copy()
    test_with_filter["news_filter_keep"] = (test_with_filter["has_event_nearby"] == 1).astype(int)
    test_trades_path = out_dir / "test_trades_with_filter.csv"
    test_with_filter[["pips", "has_event_nearby", "news_filter_keep", "event_impact", "minutes_since_event"]].to_csv(test_trades_path, index=False)
    print(f"✅ Test trades saved: {test_trades_path}")
    
    # Save gate results
    gate_results = pd.DataFrame([{
        "gate": "PF >= 1.25",
        "passed": gate_pf,
        "value": test_news_pf,
        "threshold": 1.25,
    }, {
        "gate": "WR >= 38%",
        "passed": gate_wr,
        "value": test_news_wr,
        "threshold": 38.0,
    }, {
        "gate": "Trades >= 15",
        "passed": gate_count,
        "value": test_news_count,
        "threshold": 15,
    }, {
        "gate": "PF improvement >= 5%",
        "passed": gate_improvement,
        "value": test_news_pf / test_baseline_pf,
        "threshold": 1.05,
    }, {
        "gate": "ALL GATES",
        "passed": all_pass,
        "value": None,
        "threshold": None,
    }])
    gate_path = out_dir / "deployment_gates.csv"
    gate_results.to_csv(gate_path, index=False)
    print(f"✅ Gates saved: {gate_path}")


if __name__ == "__main__":
    main()
