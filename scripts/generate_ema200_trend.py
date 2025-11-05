"""Generate a per-day EMA200 trend file (Up/Down) from a combined 1-minute CSV.

Output: `data/ema200_trend_by_date.csv` with columns:
        date (YYYY-MM-DD), trend (Up|Down)

Notes:
- Trend is computed from a 15-minute resampled series (Close), EMA200 via pandas EWM.
- Sampling time is 12:45 at UTC+1 (i.e., 11:45 UTC); we implement this by shifting
    the index +1 hour, then selecting 12:45, and finally writing just the UTC date.
"""
from pathlib import Path
import argparse
import pandas as pd


def _read_csv_auto(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=[0], infer_datetime_format=True)
    # Ensure timestamp is first column; normalize to UTC
    df.columns = [c if i != 0 else "timestamp" for i, c in enumerate(df.columns)]
    df = df.rename(columns={c: c.strip() for c in df.columns})
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp").sort_index()
    return df


def main():
    parser = argparse.ArgumentParser(description="Generate EMA200 trend per-day (Up/Down)")
    parser.add_argument(
        "--input-csv",
        default="data/combined_xauusd_1min_full.csv",
        help="Combined 1-minute CSV input (default: data/combined_xauusd_1min_full.csv)",
    )
    parser.add_argument(
        "--out-csv",
        default="data/ema200_trend_by_date.csv",
        help="Output CSV path (default: data/ema200_trend_by_date.csv)",
    )
    parser.add_argument("--time", default="12:45", help="Time (HH:MM) to sample after shifting +1h (default 12:45)")
    parser.add_argument("--shift-hours", type=int, default=1, help="Hours to shift timestamps before sampling (default 1)")
    parser.add_argument("--resample", default="15min", help="Resample timeframe for EMA (default: 15min)")
    args = parser.parse_args()

    inp = Path(args.input_csv)
    out = Path(args.out_csv)
    if not inp.exists():
        raise SystemExit(f"Input file not found: {inp}")

    df = _read_csv_auto(inp)

    # normalize column names to lowercase for robustness
    df.columns = [c.lower() for c in df.columns]
    if "close" not in df.columns:
        raise SystemExit("Input CSV must contain a Close column (case-insensitive).")

    # Resample to the requested timeframe (default 15min) and compute EMA200 on Close
    m = df["close"].to_frame()
    m15 = m.resample(args.resample).last()
    m15["ema_200"] = m15["close"].ewm(span=200, adjust=False).mean()

    # shift index by configured hours and sample at the desired time (12:45 @ UTC+1)
    shifted = m15.copy()
    shifted.index = shifted.index + pd.Timedelta(hours=args.shift_hours)

    hh, mm = map(int, args.time.split(":"))
    sample_time = pd.Timestamp(f"{hh:02d}:{mm:02d}:00").time()
    mask = (shifted.index.time == sample_time)
    sampled = shifted.loc[mask]

    if sampled.empty:
        raise SystemExit("No rows found at the sample time — check the input CSV and --time/--shift-hours args.")

    # Build output: one row per sampled timestamp with date and trend (both Up/Down saved)
    out_df = pd.DataFrame({
        "date": sampled.index.tz_convert("UTC").date,
        "trend": (sampled["close"] > sampled["ema_200"]).map({True: "Up", False: "Down"}),
    })
    # Drop duplicates by date (should be unique already)
    out_df = out_df.drop_duplicates(subset=["date"]).sort_values("date")
    out.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out, index=False)
    print(f"✅ Saved trend file to: {out} (rows: {len(out_df)})")


if __name__ == "__main__":
    main()
