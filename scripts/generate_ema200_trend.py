"""Generate per-day EMA200 trend files (Up/Down) from a combined 1-minute CSV.

Default outputs:
        data/ema200_trend_by_date_5m.csv
        data/ema200_trend_by_date_15m.csv
        data/ema200_trend_by_date_30m.csv
        data/ema200_trend_by_date_1h.csv
        data/ema200_trend_by_date_4h.csv

Each CSV contains: date (YYYY-MM-DD), trend (Up|Down)

Notes:
- Trend is computed from a resampled series (Close), EMA200 via pandas EWM.
- Sampling time is 12:45 at UTC+1 (i.e., 11:45 UTC). We implement this by shifting
    the index +1 hour, then, for each UTC date, selecting the last resampled bar
    whose time-of-day is <= 12:45. This is robust for 1h/4h bars (e.g., selects 12:00).
"""
from pathlib import Path
import argparse
from typing import List, Tuple
import pandas as pd


def _read_csv_auto(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=[0], infer_datetime_format=True)
    # Ensure timestamp is first column; normalize to UTC
    df.columns = [c if i != 0 else "timestamp" for i, c in enumerate(df.columns)]
    df = df.rename(columns={c: c.strip() for c in df.columns})
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp").sort_index()
    return df


def _normalize_freq_label(freq: str) -> Tuple[str, str]:
    """Map user-friendly frequency to (pandas_freq, label)."""
    f = freq.strip().lower()
    mapping = {
        "1m": ("1min", "1m"),
        "1min": ("1min", "1m"),
        "5m": ("5min", "5m"),
        "5min": ("5min", "5m"),
        "15m": ("15min", "15m"),
        "15min": ("15min", "15m"),
        "30m": ("30min", "30m"),
        "30min": ("30min", "30m"),
        "1h": ("1h", "1h"),
        "60m": ("1h", "1h"),
        "4h": ("4h", "4h"),
        "240m": ("4h", "4h"),
    }
    return mapping.get(f, (f, f))


def _sample_at_or_before(df_resampled: pd.DataFrame, time_str: str) -> pd.DataFrame:
    """For each UTC date, select the last row whose (shifted) time-of-day <= target time.

    Assumes df_resampled index is tz-aware UTC.
    """
    hh, mm = map(int, time_str.split(":"))
    target_time = pd.Timestamp(f"{hh:02d}:{mm:02d}:00").time()
    # Build helper columns
    s = df_resampled.copy()
    s["date"] = s.index.tz_convert("UTC").date
    s["tod"] = s.index.time
    # Keep rows on/before target time
    s = s[s["tod"] <= target_time]
    # For each date, take last row
    s = s.reset_index().sort_values(["date", "timestamp"]).groupby("date", as_index=False).tail(1)
    s = s.set_index("timestamp").sort_index()
    return s


def main():
    parser = argparse.ArgumentParser(description="Generate EMA200 trend per-day (Up/Down)")
    parser.add_argument(
        "--input-csv",
        default="data/combined_xauusd_1min_full.csv",
        help="Combined 1-minute CSV input (default: data/combined_xauusd_1min_full.csv)",
    )
    parser.add_argument(
        "--out-csv",
        default="results/trends/ema200_trend_by_date_1m.csv",
        help="Single-output CSV path (default: results/trends/ema200_trend_by_date_1m.csv). If --resamples is provided, this path becomes a compatibility alias (prefer 1m if generated).",
    )
    parser.add_argument("--time", default="12:45", help="Fallback sample time (HH:MM) used if a timeframe-specific time isn't provided")
    parser.add_argument("--shift-hours", type=int, default=1, help="Hours to shift timestamps before sampling (default 1; used to emulate prior 11:45 logic)")
    parser.add_argument("--resample", default="15min", help="Single resample timeframe for EMA (default: 15min)")
    parser.add_argument(
        "--resamples",
        default="1m,5m,15m,30m,1h,4h",
        help="Comma-separated list of resample frames to generate in one run. Example: 1m,5m,15m,30m,1h,4h",
    )
    parser.add_argument(
        "--sample-times",
        default="1m=11:59,5m=11:55,15m=11:45,30m=11:30,1h=12:00,4h=12:00",
        help="Per-timeframe UTC cutoff times applied BEFORE overlap (format: tf=HH:MM,...). Close of last bar at or before each time is used.",
    )
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

    # Determine whether to run multi-output mode
    multi_list: List[str] = [x.strip() for x in (args.resamples or "").split(",") if x.strip()]
    # Parse per-timeframe times
    def _parse_time_map(s: str) -> dict:
        out = {}
        for part in [p for p in (s or '').split(',') if p.strip()]:
            if '=' not in part:
                continue
            k,v = part.split('=',1)
            k = k.strip().lower()
            v = v.strip()
            try:
                hh,mm = map(int,v.split(':'))
                if not (0 <= hh <= 23 and 0 <= mm <= 59):
                    continue
            except Exception:
                continue
            out[k]=v
        return out

    time_map = _parse_time_map(args.sample_times)

    def _add_minutes(time_str: str, minutes: int) -> str:
        hh, mm = map(int, time_str.split(':'))
        base = pd.Timestamp(f"2000-01-01 {hh:02d}:{mm:02d}:00", tz='UTC')
        shifted = base + pd.Timedelta(minutes=minutes)
        return shifted.strftime('%H:%M')

    if multi_list:
        saved_any = False
        alias_1m_path = None
        fifteen_path = None
        for f in multi_list:
            pandas_freq, label = _normalize_freq_label(f)
            # Use Close price; pick last bar at or before timeframe-specific cutoff
            m = df["close"].to_frame()
            rs = m.resample(pandas_freq).last()
            rs["ema_200"] = rs["close"].ewm(span=200, adjust=False).mean()
            shifted = rs.copy()
            shifted.index = shifted.index + pd.Timedelta(hours=args.shift_hours)
            cutoff = time_map.get(label, args.time)
            effective_cutoff = _add_minutes(cutoff, args.shift_hours * 60)
            sampled = _sample_at_or_before(shifted, effective_cutoff)
            if sampled.empty:
                print(f"⚠️ No rows found for {label} at/before {cutoff}; skipping.")
                continue
            out_df = pd.DataFrame({
                "date": sampled.index.tz_convert("UTC").date,
                "trend": (sampled["close"] > sampled["ema_200"]).map({True: "Up", False: "Down"}),
            })
            out_df = out_df.drop_duplicates(subset=["date"]).sort_values("date")
            # Build output path with suffix in the same folder as --out-csv
            out_base = Path(args.out_csv)
            # Keep timeframe files together in same folder as out-csv
            out_tf = out_base.parent / f"ema200_trend_by_date_{label}.csv"
            out_tf.parent.mkdir(parents=True, exist_ok=True)
            out_df.to_csv(out_tf, index=False)
            print(f"✅ Saved trend file to: {out_tf} (rows: {len(out_df)})")
            saved_any = True
            if label == "1m":
                alias_1m_path = out_tf
            if label == "15m":
                fifteen_path = out_tf
        # For compatibility, also write the requested file name as 1m if generated; otherwise 15m
        compat = Path(args.out_csv)
        compat.parent.mkdir(parents=True, exist_ok=True)
        if alias_1m_path is not None and Path(alias_1m_path).resolve() != compat.resolve():
            pd.read_csv(alias_1m_path).to_csv(compat, index=False)
            print(f"✅ Wrote compatibility file: {compat} (alias of 1m)")
        elif alias_1m_path is None and fifteen_path is not None and Path(fifteen_path).resolve() != compat.resolve():
            pd.read_csv(fifteen_path).to_csv(compat, index=False)
            print(f"✅ Wrote compatibility file: {compat} (alias of 15m)")
        if not saved_any:
            raise SystemExit("No outputs were generated; check resamples/time settings.")
        return

    # Single-output mode (use fallback time)
    m = df["close"].to_frame()
    rs = m.resample(args.resample).last()
    rs["ema_200"] = rs["close"].ewm(span=200, adjust=False).mean()
    shifted = rs.copy()
    shifted.index = shifted.index + pd.Timedelta(hours=args.shift_hours)
    cutoff = args.time
    effective_cutoff = _add_minutes(cutoff, args.shift_hours * 60)
    sampled = _sample_at_or_before(shifted, effective_cutoff)
    if sampled.empty:
        raise SystemExit("No rows found at/before sample cutoff — check the input CSV and --time/--shift-hours args.")
    out_df = pd.DataFrame({
        "date": sampled.index.tz_convert("UTC").date,
        "trend": (sampled["close"] > sampled["ema_200"]).map({True: "Up", False: "Down"}),
    })
    out_df = out_df.drop_duplicates(subset=["date"]).sort_values("date")
    out.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out, index=False)
    print(f"✅ Saved trend file to: {out} (rows: {len(out_df)})")


if __name__ == "__main__":
    main()
