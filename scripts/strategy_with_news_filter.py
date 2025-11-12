"""
SuperTrend strategy with GDELT news sentiment filter integration.

This extends the base strategy with a news filter that trades only when:
- headline_count >= 5 (sufficient news coverage)
- net_sentiment < -0.1 (moderate bearish sentiment for gold)

The filter acts as a contrarian signal: when news is bearish but SuperTrend
still triggers, it catches oversold bounces.
"""

import os
import sys
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class StrategyConfig:
    st_length: int = 10
    st_multiplier: float = 3.6
    max_sl_distance_pips: float = 520.0
    pip_size: float = 0.01
    entry_hours: Optional[Tuple[int, int]] = (13, 16)
    filter_days: Optional[set] = None
    allowed_sides: Optional[set] = None
    # News filter parameters
    use_news_filter: bool = False
    news_sentiment_parquet: Optional[str] = None
    min_headline_count: int = 5
    filter_type: str = "bearish"  # "bearish", "bullish", or "combined"
    bearish_threshold: float = -0.1  # net_sentiment < this for bearish
    bullish_threshold: float = 0.3   # net_sentiment > this for bullish


def rma(series: pd.Series, length: int) -> pd.Series:
    """Pine RMA: EMA with alpha = 1/length, seeded by SMA."""
    alpha = 1.0 / length
    sma = series.rolling(length, min_periods=length).mean()
    r = pd.Series(index=series.index, dtype=float)
    if len(series) >= length:
        r.iloc[length - 1] = sma.iloc[length - 1]
    for i in range(length, len(series)):
        prev = r.iloc[i - 1]
        r.iloc[i] = alpha * series.iloc[i] + (1 - alpha) * prev
    return r


def compute_supertrend(df: pd.DataFrame, length: int, multiplier: float) -> Tuple[pd.Series, pd.Series]:
    """Compute SuperTrend direction (+1/-1) and line using an ATR based on RMA."""
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    close = df["Close"].astype(float)

    hl2 = (high + low) / 2.0
    tr = pd.concat([
        (high - low),
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1, skipna=True)
    atr = rma(tr, length)

    upperband = hl2 + multiplier * atr
    lowerband = hl2 - multiplier * atr

    direction = pd.Series(index=df.index, dtype=float)
    supertrend = pd.Series(index=df.index, dtype=float)

    for i in range(len(df)):
        if i == 0 or np.isnan(atr.iloc[i]):
            direction.iloc[i] = np.nan
            supertrend.iloc[i] = np.nan
            continue

        if direction.iloc[i - 1] == 1:
            lowerband.iloc[i] = max(lowerband.iloc[i], lowerband.iloc[i - 1])
            if close.iloc[i] < lowerband.iloc[i]:
                direction.iloc[i] = -1
                supertrend.iloc[i] = upperband.iloc[i]
            else:
                direction.iloc[i] = 1
                supertrend.iloc[i] = lowerband.iloc[i]
        elif direction.iloc[i - 1] == -1:
            upperband.iloc[i] = min(upperband.iloc[i], upperband.iloc[i - 1])
            if close.iloc[i] > upperband.iloc[i]:
                direction.iloc[i] = 1
                supertrend.iloc[i] = lowerband.iloc[i]
            else:
                direction.iloc[i] = -1
                supertrend.iloc[i] = upperband.iloc[i]
        else:
            if close.iloc[i] >= hl2.iloc[i]:
                direction.iloc[i] = 1
                supertrend.iloc[i] = lowerband.iloc[i]
            else:
                direction.iloc[i] = -1
                supertrend.iloc[i] = upperband.iloc[i]

    return direction, supertrend


def within_entry_hours(ts: pd.Timestamp, entry_hours: Optional[Tuple[int, int]]) -> bool:
    if entry_hours is None:
        return True
    start_h, end_h = entry_hours
    return start_h <= ts.hour < end_h


def load_news_sentiment(parquet_path: str) -> pd.DataFrame:
    """Load GDELT sentiment features from parquet file."""
    if not os.path.exists(parquet_path):
        raise FileNotFoundError(f"News sentiment file not found: {parquet_path}")
    
    df = pd.read_parquet(parquet_path)
    # Ensure entry_time is datetime
    df['entry_time'] = pd.to_datetime(df['entry_time'], utc=True)
    return df


def passes_news_filter(entry_time: pd.Timestamp, sentiment_df: pd.DataFrame, 
                       min_headline_count: int, filter_type: str,
                       bearish_threshold: float, bullish_threshold: float) -> bool:
    """
    Check if trade passes news sentiment filter.
    
    Filter types:
    - "bearish": moderate_bearish (net_sentiment < bearish_threshold, default -0.1)
    - "bullish": strong_bullish (net_sentiment > bullish_threshold, default 0.3)
    - "combined": Either bearish OR bullish passes
    
    All require headline_count >= min_headline_count
    
    Returns True if filter passes, False otherwise.
    """
    # Find matching sentiment record
    match = sentiment_df[sentiment_df['entry_time'] == entry_time]
    
    if match.empty:
        # No sentiment data for this timestamp
        return False
    
    row = match.iloc[0]
    headline_count = row.get('headline_count', 0)
    net_sentiment = row.get('net_sentiment', 0)
    
    # Check headline count first
    if headline_count < min_headline_count:
        return False
    
    # Apply filter type
    if filter_type == "bearish":
        # moderate_bearish: bearish sentiment
        return net_sentiment < bearish_threshold
    elif filter_type == "bullish":
        # strong_bullish: bullish sentiment
        return net_sentiment > bullish_threshold
    elif filter_type == "combined":
        # Either bearish OR bullish
        return (net_sentiment < bearish_threshold) or (net_sentiment > bullish_threshold)
    else:
        raise ValueError(f"Unknown filter_type: {filter_type}")
    
    return False


def backtest_supertrend(df: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    """Backtest SuperTrend strategy with optional news filter."""
    if df.empty:
        return pd.DataFrame(columns=["entry_time", "exit_time", "side", "entry", "exit", 
                                    "final_stop", "pips", "passed_news_filter"])

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df.set_index("timestamp", inplace=True)
    df = df.sort_index()

    if cfg.filter_days:
        mask = pd.Series([ts.date() in cfg.filter_days for ts in df.index], index=df.index)
        df = df[mask]
        if df.empty:
            return pd.DataFrame(columns=["entry_time", "exit_time", "side", "entry", "exit", 
                                        "final_stop", "pips", "passed_news_filter"])

    # Load news sentiment if filter enabled
    sentiment_df = None
    if cfg.use_news_filter and cfg.news_sentiment_parquet:
        try:
            sentiment_df = load_news_sentiment(cfg.news_sentiment_parquet)
            print(f"✅ Loaded news sentiment features: {len(sentiment_df)} trades")
        except Exception as e:
            print(f"⚠️ Failed to load news sentiment: {e}")
            print("   Proceeding without news filter.")
            cfg.use_news_filter = False

    direction, st = compute_supertrend(df, cfg.st_length, cfg.st_multiplier)
    df["direction"] = direction
    df["supertrend"] = st

    trades = []
    position: Optional[Tuple[str, pd.Timestamp, float, float]] = None
    pending_entry: Optional[dict] = None
    direction_prev: Optional[float] = None
    prev_supertrend: Optional[float] = None

    def pips_between(a: float, b: float) -> float:
        return abs(float(a) - float(b)) / cfg.pip_size

    idx = list(df.index)
    n = len(idx)
    
    for i in range(1, n):
        ts = idx[i]
        current_direction = df.iloc[i]["direction"]
        prior_supertrend = prev_supertrend
        st_raw = df.iloc[i]["supertrend"]
        supertrend = float(st_raw) if not np.isnan(st_raw) else (float(prior_supertrend) if prior_supertrend is not None else np.nan)

        # 1) Activate pending entry
        if pending_entry is not None and ts >= pending_entry["entry_idx"]:
            if within_entry_hours(ts, cfg.entry_hours) and position is None:
                st_now = df.loc[ts, "supertrend"]
                if not np.isnan(st_now):
                    entry_price = float(df.loc[ts, "Close"])
                    if pips_between(entry_price, st_now) <= cfg.max_sl_distance_pips:
                        # Apply news filter if enabled
                        passed_filter = True
                        if cfg.use_news_filter and sentiment_df is not None:
                            passed_filter = passes_news_filter(
                                ts, sentiment_df, 
                                cfg.min_headline_count,
                                cfg.filter_type,
                                cfg.bearish_threshold,
                                cfg.bullish_threshold
                            )
                        
                        if passed_filter:
                            position = (pending_entry["side"], ts, entry_price, float(st_now))
                        else:
                            # Trade filtered out by news
                            trades.append({
                                "entry_time": ts,
                                "exit_time": None,
                                "side": pending_entry["side"],
                                "entry": entry_price,
                                "exit": None,
                                "final_stop": None,
                                "pips": None,
                                "passed_news_filter": False,
                            })
            pending_entry = None

        # 2) Manage open position
        if position is not None:
            side, ent_time, ent_price, sl_price = position
            trail_st = supertrend if not np.isnan(supertrend) else prior_supertrend
            if side == "long" and current_direction != 1:
                trail_st = prior_supertrend
            elif side == "short" and current_direction != -1:
                trail_st = prior_supertrend

            if trail_st is not None and not np.isnan(trail_st):
                if side == "long" and trail_st > sl_price:
                    sl_price = float(trail_st)
                elif side == "short" and trail_st < sl_price:
                    sl_price = float(trail_st)

            low_now = float(df.iloc[i]["Low"])
            high_now = float(df.iloc[i]["High"])
            exit_hit = (side == "long" and trail_st is not None and not np.isnan(trail_st) and low_now <= trail_st) or \
                       (side == "short" and trail_st is not None and not np.isnan(trail_st) and high_now >= trail_st)
            
            if exit_hit:
                exit_price = float(prior_supertrend) if (prior_supertrend is not None and not np.isnan(prior_supertrend)) else (low_now if side == "long" else high_now)
                pnl_pips = (exit_price - ent_price) / cfg.pip_size * (1 if side == "long" else -1)
                trades.append({
                    "entry_time": ent_time,
                    "exit_time": ts,
                    "side": side,
                    "entry": ent_price,
                    "exit": exit_price,
                    "final_stop": sl_price,
                    "pips": pnl_pips,
                    "passed_news_filter": True,
                })
                position = None
            else:
                position = (side, ent_time, ent_price, sl_price)

        # 3) Schedule new entries
        if not within_entry_hours(ts, cfg.entry_hours) or pending_entry is not None:
            direction_prev = current_direction
            prev_supertrend = supertrend if not np.isnan(supertrend) else prior_supertrend
            continue

        prev_dir = df.iloc[i - 1]["direction"]
        curr_dir = current_direction
        if np.isnan(prev_dir) or np.isnan(curr_dir) or prev_dir == curr_dir:
            direction_prev = current_direction
            prev_supertrend = supertrend if not np.isnan(supertrend) else prior_supertrend
            continue

        curr_open = float(df.iloc[i]["Open"])
        curr_close = float(df.iloc[i]["Close"])
        flip_bull = prev_dir == -1 and curr_dir == 1
        flip_bear = prev_dir == 1 and curr_dir == -1

        C0_green = curr_close > curr_open
        C0_red = curr_close < curr_open

        if flip_bull and C0_green:
            if i + 1 >= n:
                direction_prev = current_direction
                prev_supertrend = supertrend if not np.isnan(supertrend) else prior_supertrend
                continue
            future = df.iloc[i + 1:]
            next_red = future[future["Close"] < future["Open"]].head(1)
            if next_red.empty:
                direction_prev = current_direction
                prev_supertrend = supertrend if not np.isnan(supertrend) else prior_supertrend
                continue
            red_ts = next_red.index[0]
            red_pos = df.index.get_loc(red_ts)
            enter_pos = red_pos + 1
            if enter_pos < n:
                enter_row = df.iloc[enter_pos]
                if float(enter_row["Close"]) > float(enter_row["Open"]):
                    if cfg.allowed_sides is None or "long" in cfg.allowed_sides:
                        pending_entry = {"entry_idx": df.index[enter_pos], "side": "long"}

        elif flip_bear and C0_red:
            if i + 1 >= n:
                direction_prev = current_direction
                prev_supertrend = supertrend if not np.isnan(supertrend) else prior_supertrend
                continue
            future = df.iloc[i + 1:]
            next_green = future[future["Close"] > future["Open"]].head(1)
            if next_green.empty:
                direction_prev = current_direction
                prev_supertrend = supertrend if not np.isnan(supertrend) else prior_supertrend
                continue
            green_ts = next_green.index[0]
            green_pos = df.index.get_loc(green_ts)
            enter_pos = green_pos + 1
            if enter_pos < n:
                enter_row = df.iloc[enter_pos]
                if float(enter_row["Close"]) < float(enter_row["Open"]):
                    if cfg.allowed_sides is None or "short" in cfg.allowed_sides:
                        pending_entry = {"entry_idx": df.index[enter_pos], "side": "short"}

        direction_prev = current_direction
        prev_supertrend = supertrend if not np.isnan(supertrend) else prior_supertrend

    return pd.DataFrame(trades)


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="SuperTrend strategy with news sentiment filter.")
    
    # Data input
    default_input_candidates = [
        r"C:\Users\Olale\Documents\Codebase\Quant\XAUI\data\twelvedata_xauusd_1min_full.csv",
        os.path.join("data", "twelvedata_xauusd_1min_full.csv"),
        os.path.join("data", "combined_xauusd_1min_full.csv"),
    ]
    default_input_csv = next((p for p in default_input_candidates if os.path.exists(p)), default_input_candidates[0])
    parser.add_argument("--input-csv", default=default_input_csv, help="Path to OHLC CSV")
    
    # Strategy parameters
    parser.add_argument("--st-length", type=int, default=10)
    parser.add_argument("--st-multiplier", type=float, default=3.6)
    parser.add_argument("--max-sl-distance-pips", type=float, default=520.0)
    parser.add_argument("--entry-hours", default="13-16", help="UTC hour window, e.g., 13-16; or 'all'")
    
    # News filter
    parser.add_argument("--use-news-filter", action="store_true", help="Enable GDELT news sentiment filter")
    parser.add_argument("--news-sentiment-parquet", default="data/features/trades_sentiment_gold_clean.parquet",
                       help="Path to sentiment features parquet")
    parser.add_argument("--filter-type", choices=["bearish", "bullish", "combined"], default="bearish",
                       help="Filter type: bearish (contrarian), bullish (momentum), or combined (both)")
    parser.add_argument("--min-headline-count", type=int, default=5, help="Minimum headlines required")
    parser.add_argument("--bearish-threshold", type=float, default=-0.1, help="Bearish sentiment threshold (net_sentiment < this)")
    parser.add_argument("--bullish-threshold", type=float, default=0.3, help="Bullish sentiment threshold (net_sentiment > this)")
    
    # Filters
    parser.add_argument("--filter-csv", default=None, help="Optional CSV with tradable dates")
    parser.add_argument("--long-only", action="store_true", help="Only long trades")
    parser.add_argument("--short-only", action="store_true", help="Only short trades")
    parser.add_argument("--both-sides", action="store_true", help="Both long and short")
    parser.add_argument("--ignore-ema-filter", action="store_true", help="Trade on all days")
    parser.add_argument("--trend", choices=["up", "down", "both"], default="up")
    
    # Output
    parser.add_argument("--out-dir", default="results/news_filtered", help="Output directory")
    parser.add_argument("--run-tag", default="", help="Tag for output files")
    
    # Date filtering
    parser.add_argument("--date-start", default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--date-end", default=None, help="End date (YYYY-MM-DD)")
    
    args = parser.parse_args(argv)

    # Parse entry hours
    if args.entry_hours.lower() == "all":
        entry_hours = None
    else:
        try:
            h0, h1 = args.entry_hours.split("-")
            entry_hours = (int(h0), int(h1))
        except Exception:
            raise SystemExit("Invalid --entry-hours. Use 'all' or 'HH-HH' like 13-16.")

    # Load data
    if not os.path.exists(args.input_csv):
        raise SystemExit(f"Input CSV not found: {args.input_csv}")
    print(f"Using input CSV: {args.input_csv}")
    df = pd.read_csv(args.input_csv)
    
    # Apply date filtering if specified
    if args.date_start or args.date_end:
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        if args.date_start:
            start_date = pd.to_datetime(args.date_start).tz_localize('UTC')
            df = df[df['timestamp'] >= start_date]
            print(f"  Filtered to start date: {args.date_start}")
        if args.date_end:
            end_date = pd.to_datetime(args.date_end).tz_localize('UTC') + pd.Timedelta(days=1)
            df = df[df['timestamp'] < end_date]
            print(f"  Filtered to end date: {args.date_end}")
        print(f"  Remaining rows: {len(df)}")

    # Filter days (EMA trend filter)
    filter_days = None
    if not args.ignore_ema_filter and args.filter_csv:
        try:
            fdf = pd.read_csv(args.filter_csv)
            if "trend" in fdf.columns and "date" in fdf.columns:
                ts = pd.to_datetime(fdf["date"], utc=True, errors="coerce").dt.date
                if args.trend == "up":
                    ups = fdf["trend"].str.strip().str.lower() == "up"
                elif args.trend == "down":
                    ups = fdf["trend"].str.strip().str.lower() == "down"
                else:
                    ups = pd.Series(True, index=fdf.index)
                filter_days = set(ts[ups].dropna().unique().tolist())
                print(f"Loaded trend filter: {len(filter_days)} {args.trend} days")
        except Exception as e:
            print(f"⚠️ Failed to load filter CSV: {e}")

    # Determine allowed sides
    if args.long_only and args.short_only:
        raise SystemExit("Cannot use both --long-only and --short-only")
    if args.both_sides:
        allowed_sides = None
    elif args.short_only:
        allowed_sides = {"short"}
    else:
        allowed_sides = {"long"}

    # Build config
    cfg = StrategyConfig(
        st_length=args.st_length,
        st_multiplier=args.st_multiplier,
        max_sl_distance_pips=args.max_sl_distance_pips,
        entry_hours=entry_hours,
        filter_days=filter_days,
        allowed_sides=allowed_sides,
        use_news_filter=args.use_news_filter,
        news_sentiment_parquet=args.news_sentiment_parquet if args.use_news_filter else None,
        filter_type=args.filter_type,
        min_headline_count=args.min_headline_count,
        bearish_threshold=args.bearish_threshold,
        bullish_threshold=args.bullish_threshold,
    )

    print(f"\n{'='*60}")
    print(f"Strategy Configuration:")
    print(f"  SuperTrend: {cfg.st_length} x {cfg.st_multiplier}")
    print(f"  Max SL Distance: {cfg.max_sl_distance_pips} pips")
    print(f"  Entry Hours: {entry_hours or 'all'}")
    print(f"  Allowed Sides: {allowed_sides or 'both'}")
    print(f"  News Filter: {'ENABLED' if cfg.use_news_filter else 'DISABLED'}")
    if cfg.use_news_filter:
        print(f"    - Filter Type: {cfg.filter_type}")
        print(f"    - Min Headlines: {cfg.min_headline_count}")
        if cfg.filter_type in ["bearish", "combined"]:
            print(f"    - Bearish Threshold: net_sentiment < {cfg.bearish_threshold}")
        if cfg.filter_type in ["bullish", "combined"]:
            print(f"    - Bullish Threshold: net_sentiment > {cfg.bullish_threshold}")
        print(f"    - Sentiment File: {cfg.news_sentiment_parquet}")
    print(f"{'='*60}\n")

    # Run backtest
    results = backtest_supertrend(df, cfg)

    # Save results
    os.makedirs(args.out_dir, exist_ok=True)
    tag = f"_{args.run_tag}" if args.run_tag else ""
    out_csv = os.path.join(args.out_dir, f"trades{tag}.csv")
    results.to_csv(out_csv, index=False)
    print(f"✅ Saved results to: {out_csv}")

    # Performance analysis
    if not results.empty:
        # Separate filtered and executed trades
        executed = results[results['passed_news_filter'] == True].copy()
        filtered_out = results[results['passed_news_filter'] == False].copy()
        
        print(f"\n{'='*60}")
        print(f"BACKTEST RESULTS")
        print(f"{'='*60}")
        print(f"Total potential trades: {len(results)}")
        print(f"  - Executed: {len(executed)}")
        print(f"  - Filtered out by news: {len(filtered_out)}")
        
        if len(executed) > 0:
            wins = (executed['pips'] > 0).sum()
            losses = (executed['pips'] < 0).sum()
            win_rate = wins / len(executed)
            avg_pips = executed['pips'].mean()
            total_pips = executed['pips'].sum()
            
            gross_gain = executed.loc[executed['pips'] > 0, 'pips'].sum()
            gross_loss = executed.loc[executed['pips'] < 0, 'pips'].sum()
            profit_factor = gross_gain / abs(gross_loss) if gross_loss != 0 else float('inf')
            
            print(f"\nExecuted Trades Performance:")
            print(f"  - Count: {len(executed)}")
            print(f"  - Win Rate: {win_rate:.2%}")
            print(f"  - Avg Pips: {avg_pips:.2f}")
            print(f"  - Total Pips: {total_pips:.1f}")
            print(f"  - Profit Factor: {profit_factor:.3f}")
            print(f"  - Best Trade: {executed['pips'].max():.1f} pips")
            print(f"  - Worst Trade: {executed['pips'].min():.1f} pips")
            
            # Equity curve and drawdown
            executed['equity'] = executed['pips'].cumsum()
            running_max = executed['equity'].cummax()
            drawdowns = executed['equity'] - running_max
            max_dd = drawdowns.min()
            print(f"  - Max Drawdown: {max_dd:.1f} pips")
        
        print(f"{'='*60}\n")
        
        # Save simplified results
        if len(executed) > 0:
            simple_df = executed[['entry_time', 'pips', 'side']].copy()
            simple_df['entry_time'] = pd.to_datetime(simple_df['entry_time'], utc=True).dt.strftime("%Y-%m-%d %H:%M")
            simple_path = os.path.join(args.out_dir, f"trades_simple{tag}.csv")
            simple_df.to_csv(simple_path, index=False)
            print(f"Saved simplified results to: {simple_path}")
    else:
        print("\n⚠️ No trades executed.")


if __name__ == "__main__":
    sys.exit(main())
