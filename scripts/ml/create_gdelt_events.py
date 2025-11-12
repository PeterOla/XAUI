"""
Create events_offline.csv for GDELT news fetching.

Generates 3-hour lookback windows for all trades to fetch relevant headlines.
"""
import pandas as pd
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Create GDELT event windows for trades")
    parser.add_argument(
        "--trades-csv",
        default="results/baseline_2015_2025_up_both_full/15m/trades.csv",
        help="Trades CSV from backtest"
    )
    parser.add_argument(
        "--out-csv",
        default="sentiments/news/events_offline.csv",
        help="Output CSV with event windows"
    )
    parser.add_argument(
        "--lookback-hours",
        type=float,
        default=3.0,
        help="Hours to look back from entry_time for news"
    )
    args = parser.parse_args()
    
    # Load trades
    print(f"Loading trades from {args.trades_csv}...")
    trades = pd.read_csv(args.trades_csv)
    trades["entry_time"] = pd.to_datetime(trades["entry_time"], utc=True)
    
    print(f"Total trades: {len(trades):,}")
    
    # Create event windows
    events = []
    for idx, row in trades.iterrows():
        entry_time = row["entry_time"]
        window_end = entry_time
        window_start = entry_time - pd.Timedelta(hours=args.lookback_hours)
        
        events.append({
            "event_index": idx,
            "entry_time": entry_time,
            "window_start": window_start,
            "window_end": window_end,
            "side": row["side"],
            "pips": row["pips"],
        })
    
    # Save
    events_df = pd.DataFrame(events)
    out_path = Path(args.out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    events_df.to_csv(out_path, index=False)
    
    print(f"\n✅ Created {len(events_df):,} event windows")
    print(f"   Lookback: {args.lookback_hours} hours")
    print(f"   Saved to: {out_path}")
    print(f"\nFirst few windows:")
    print(events_df[["event_index", "entry_time", "window_start", "window_end"]].head(5))
    print(f"\n📊 Date range: {events_df['entry_time'].min()} to {events_df['entry_time'].max()}")


if __name__ == "__main__":
    main()
