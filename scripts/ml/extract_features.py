"""
Extract primary and secondary (context) features per trade for ML Phase 3A.
Outputs: data/features/trades_features.parquet + feature_meta.json
"""
import argparse
import os
from pathlib import Path
import json
import pandas as pd
import numpy as np

def infer_time_col(df: pd.DataFrame):
    for c in df.columns:
        cl = c.lower()
        if cl in ("timestamp","time","datetime","date","datetimeutc","t"):
            return c
    return df.columns[0]

def to_utc_index(df: pd.DataFrame, time_col: str):
    ts = pd.to_datetime(df[time_col], utc=True, errors="coerce")
    df = df.dropna(subset=[time_col]).copy()
    df.index = ts
    return df.drop(columns=[time_col]).sort_index()

def resample_ohlc(df: pd.DataFrame, rule: str):
    o = df["Open"].resample(rule).first()
    h = df["High"].resample(rule).max()
    l = df["Low"].resample(rule).min()
    c = df["Close"].resample(rule).last()
    out = pd.DataFrame({"Open":o,"High":h,"Low":l,"Close":c}).dropna()
    return out

def atr(df15: pd.DataFrame, period: int = 14):
    high = df15["High"]; low = df15["Low"]; close = df15["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()

def ema(series: pd.Series, span: int = 200):
    return series.ewm(span=span, adjust=False).mean()

def session_from_hour(h: int):
    # UTC sessions (simple buckets):
    # Asia: 00:00–06:59, London: 07:00–11:59, Overlap: 12:00–16:00, NY: 13:00–20:59, Off: 21:00–23:59
    if 0 <= h <= 6: return "asia"
    if 7 <= h <= 11: return "london_pre_overlap"
    if h == 12: return "overlap"
    if 13 <= h <= 16: return "overlap"
    if 17 <= h <= 20: return "ny_late"
    return "off"

def load_trend_map(trend_csv_path: str):
    if not os.path.exists(trend_csv_path):
        return {}
    d = pd.read_csv(trend_csv_path)
    date_col = "date" if "date" in d.columns else ("Date" if "Date" in d.columns else None)
    if not date_col or "trend" not in d.columns:
        return {}
    d["date"] = pd.to_datetime(d[date_col]).dt.date
    d["up"] = d["trend"].astype(str).str.strip().str.lower().eq("up")
    return {r["date"]: bool(r["up"]) for _, r in d.iterrows()}

def build_upcount(entry_date: pd.Timestamp, tfs: list, trend_dir: str = "data/trend"):
    d = entry_date.date()
    ups = {}
    for tf in tfs:
        path = os.path.join(trend_dir, f"ema200_trend_by_date_{tf}.csv")
        m = load_trend_map(path)
        ups[tf] = m.get(d, False)
    count = sum(1 for v in ups.values() if v)
    return count, ups

def asian_range_for_date(df15: pd.DataFrame, date_utc: pd.Timestamp):
    # Asia 00:00–06:59 UTC
    day = date_utc.normalize()
    asia_start = day
    asia_end = day + pd.Timedelta(hours=6, minutes=59)
    seg = df15.loc[(df15.index >= asia_start) & (df15.index <= asia_end)]
    if seg.empty:
        return np.nan, np.nan, np.nan
    return float(seg["High"].max() - seg["Low"].min()), float(seg["High"].max()), float(seg["Low"].min())

def london_open_range(df15: pd.DataFrame, date_utc: pd.Timestamp):
    # 07:00–07:59 UTC
    start = date_utc.normalize() + pd.Timedelta(hours=7)
    end = start + pd.Timedelta(hours=0, minutes=59)
    seg = df15.loc[(df15.index >= start) & (df15.index <= end)]
    if seg.empty:
        return np.nan
    return float(seg["High"].max() - seg["Low"].min())

def add_secondary_context_features(df_feats: pd.DataFrame, df15: pd.DataFrame):
    # Asian range, breakout flags, session bucket one-hots, London open range
    asia_ranges = []
    asia_highs = []
    asia_lows = []
    lon_open_ranges = []
    is_asia = []
    is_london = []
    is_overlap = []
    is_ny = []
    is_off = []
    entry_above_asia_high = []
    entry_below_asia_low = []
    session_idx = []

    for ts, row in df_feats.iterrows():
        rng, a_hi, a_lo = asian_range_for_date(df15, ts)
        asia_ranges.append(rng); asia_highs.append(a_hi); asia_lows.append(a_lo)
        lon_open_ranges.append(london_open_range(df15, ts))
        h = ts.hour
        sess = session_from_hour(h); session_idx.append(sess)
        is_asia.append(1 if sess == "asia" else 0)
        is_london.append(1 if sess == "london_pre_overlap" else 0)
        is_overlap.append(1 if sess == "overlap" else 0)
        is_ny.append(1 if sess == "ny_late" else 0)
        is_off.append(1 if sess == "off" else 0)
        close_px = row["close"]
        entry_above_asia_high.append(1 if (not np.isnan(a_hi) and close_px > a_hi) else 0)
        entry_below_asia_low.append(1 if (not np.isnan(a_lo) and close_px < a_lo) else 0)

    df_feats["sec_asia_range"] = asia_ranges
    df_feats["sec_london_open_range"] = lon_open_ranges
    df_feats["sec_is_asia"] = is_asia
    df_feats["sec_is_london"] = is_london
    df_feats["sec_is_overlap"] = is_overlap
    df_feats["sec_is_ny_late"] = is_ny
    df_feats["sec_is_off"] = is_off
    df_feats["sec_entry_above_asia_high"] = entry_above_asia_high
    df_feats["sec_entry_below_asia_low"] = entry_below_asia_low
    df_feats["sec_session"] = session_idx
    # Normalize ranges by ATR to make them scale-free where possible
    eps = 1e-9
    if "atr14" in df_feats.columns:
        df_feats["sec_asia_range_atr"] = df_feats["sec_asia_range"] / (df_feats["atr14"] + eps)
        df_feats["sec_london_open_range_atr"] = df_feats["sec_london_open_range"] / (df_feats["atr14"] + eps)
    return df_feats

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades-csv", default=os.path.join("results","trends","15m","trades_simple_up_buy_only.csv"))
    ap.add_argument("--input-csv", default=os.path.join("data","twelvedata_xauusd_1min_full.csv"))
    ap.add_argument("--timeframe", default="15m")
    ap.add_argument("--trend-tfs", default="1m,5m,15m,30m,1h")
    ap.add_argument("--out-parquet", default=os.path.join("data","features","trades_features.parquet"))
    ap.add_argument("--out-csv", default=os.path.join("data","features","trades_features.csv"))
    ap.add_argument("--meta-json", default=os.path.join("data","features","feature_meta.json"))
    args = ap.parse_args()

    Path(os.path.join("data","features")).mkdir(parents=True, exist_ok=True)

    trades = pd.read_csv(args.trades_csv)
    # Expect columns: entry_time, pips, entry, etc.
    # Make robust: find entry time and pips
    entry_col = None
    for c in trades.columns:
        if "entry_time" in c.lower():
            entry_col = c; break
    if entry_col is None:
        raise ValueError("Could not find entry_time column in trades CSV.")
    pips_col = None
    for c in trades.columns:
        if c.lower() == "pips" or "pips" in c.lower():
            pips_col = c; break
    if pips_col is None:
        raise ValueError("Could not find pips column in trades CSV.")

    trades["entry_time"] = pd.to_datetime(trades[entry_col], utc=True)
    trades = trades.sort_values("entry_time").reset_index(drop=True)

    # Load base data and resample to target timeframe
    price_raw = pd.read_csv(args.input_csv)
    time_col = infer_time_col(price_raw)
    # Standardize column names
    cols = {c:c for c in price_raw.columns}
    for k in list(cols):
        lk = k.lower()
        if lk in ("open","o"): cols[k] = "Open"
        if lk in ("high","h"): cols[k] = "High"
        if lk in ("low","l"): cols[k] = "Low"
        if lk in ("close","c"): cols[k] = "Close"
    price_raw = price_raw.rename(columns=cols)
    required = {"Open","High","Low","Close"}
    if not required.issubset(set(price_raw.columns)):
        raise ValueError("Input CSV must contain Open, High, Low, Close columns.")
    price = to_utc_index(price_raw, time_col)
    price_15 = resample_ohlc(price, args.timeframe)

    # Indicators
    price_15["ema200"] = ema(price_15["Close"], span=200)
    price_15["atr14"] = atr(price_15, period=14)

    # Build base (primary) features aligned to entry bars
    idx = []
    feat_rows = []
    for _, tr in trades.iterrows():
        ts = pd.Timestamp(tr["entry_time"])
        # Align to the bar at or before entry
        bar_ts = price_15.index[price_15.index.get_indexer([ts], method="pad")[0]]
        row = price_15.loc[bar_ts]
        high_low = max(row["High"] - row["Low"], 1e-9)
        body = abs(row["Close"] - row["Open"])
        upper_wick = row["High"] - max(row["Close"], row["Open"])
        lower_wick = min(row["Close"], row["Open"]) - row["Low"]
        feat = {
            "close": float(row["Close"]),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "range": float(high_low),
            "body_pct": float(body / high_low),
            "upper_wick_pct": float(max(upper_wick,0.0) / high_low),
            "lower_wick_pct": float(max(lower_wick,0.0) / high_low),
            "ema200": float(row["ema200"]),
            "ema_dist": float(row["Close"] - row["ema200"]),
            "ema_dist_atr": float((row["Close"] - row["ema200"]) / (row["atr14"] + 1e-9)),
            "atr14": float(row["atr14"]),
            "hour": bar_ts.hour,
            "dow": bar_ts.weekday(),
            "date": bar_ts.date(),
            "pips": float(tr[pips_col]),
            "label_win": 1 if float(tr[pips_col]) > 0 else 0,
        }
        # Up-count across TFs
        tfs = [t.strip() for t in args.trend_tfs.split(",") if t.strip()]
        up_count, ups = build_upcount(bar_ts, tfs, trend_dir=os.path.join("data","trend"))
        feat["up_count"] = up_count
        for tf, is_up in ups.items():
            feat[f"tf_{tf}_up"] = int(is_up)

        idx.append(bar_ts)
        feat_rows.append(feat)

    feats = pd.DataFrame(feat_rows, index=idx)
    feats.index.name = "entry_bar"

    # Secondary/context features
    feats = add_secondary_context_features(feats, price_15)

    # Export
    feats.to_parquet(args.out_parquet, index=True)
    feats.to_csv(args.out_csv, index=True)

    # Meta: record which columns are secondary
    secondary_cols = sorted([c for c in feats.columns if c.startswith("sec_")])
    primary_cols = sorted([c for c in feats.columns if c not in secondary_cols and c not in ("pips","label_win","date")])
    meta = {
        "rows": len(feats),
        "primary_cols": primary_cols,
        "secondary_cols": secondary_cols,
        "label_col": "label_win",
        "pips_col": "pips",
        "time_index": "entry_bar",
        "source": {
            "trades_csv": args.trades_csv,
            "input_csv": args.input_csv,
            "timeframe": args.timeframe,
            "trend_tfs": args.trend_tfs,
        }
    }
    Path(args.meta_json).parent.mkdir(parents=True, exist_ok=True)
    with open(args.meta_json, "w") as f:
        json.dump(meta, f, indent=2, default=str)

    print(f"✅ Features saved: {args.out_parquet} ({len(feats)} rows)")
    print(f"   Secondary columns: {len(secondary_cols)} | Primary columns: {len(primary_cols)}")
    print(f"   Metadata: {args.meta_json}")

if __name__ == "__main__":
    main()
