"""
Build daily regime features (Phase 3B).
Aggregates per-day indicators: EMA z-scores, slopes, volatility, up-count, prior pips, equity slope.
"""
import argparse
import os
from pathlib import Path
import pandas as pd
import numpy as np

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-csv", default=os.path.join("data","twelvedata_xauusd_1min_full.csv"))
    ap.add_argument("--trades-csv", default=os.path.join("results","trends","15m","trades_simple_up_buy_only.csv"))
    ap.add_argument("--out-parquet", default=os.path.join("data","features","daily_regime_features.parquet"))
    args = ap.parse_args()

    Path(os.path.dirname(args.out_parquet)).mkdir(parents=True, exist_ok=True)

    # TODO: Implement per-day feature aggregation logic
    # - Load OHLC, compute EMA distances per TF, slopes, volatility compression
    # - Join with per-day trade results (sum pips, count)
    # - Label: Strong (>75th pct), Neutral (25–75), Avoid (<25 or negative)

    print("⚠️ build_daily_regime_features.py is a stub. Implement per-day feature logic.")

if __name__ == "__main__":
    main()
