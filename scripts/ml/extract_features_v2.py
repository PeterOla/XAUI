"""
Enhanced feature extraction for both-sides ML (v2).
Captures entry pattern context: flip bar (C0), alternating bar (C1), entry bar (C2).
Removes price-dependent features, focuses on pattern quality and directional contrast.
"""
import argparse
import os
import json
from pathlib import Path
import pandas as pd
import numpy as np

def resample_ohlc(df: pd.DataFrame, rule: str):
    """Resample 1-minute OHLC to specified timeframe."""
    o = df["Open"].resample(rule).first()
    h = df["High"].resample(rule).max()
    l = df["Low"].resample(rule).min()
    c = df["Close"].resample(rule).last()
    out = pd.DataFrame({"Open": o, "High": h, "Low": l, "Close": c}).dropna()
    return out

def atr(df: pd.DataFrame, period: int = 14):
    """Calculate Average True Range."""
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()

def compute_supertrend_direction(df: pd.DataFrame, length: int = 10, multiplier: float = 3.6):
    """
    Compute SuperTrend direction (+1/-1) and SuperTrend level matching base_strategy.py logic.
    Returns tuple: (direction_series, supertrend_series)
    - direction: +1 for bullish, -1 for bearish
    - supertrend: the actual ST price level (lowerband when bullish, upperband when bearish)
    """
    high, low, close = df["High"], df["Low"], df["Close"]
    hl2 = (high + low) / 2.0
    
    # ATR using RMA (EMA with alpha=1/length)
    tr = pd.concat([
        (high - low).abs(),
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1, skipna=True)
    
    alpha = 1.0 / length
    atr_series = pd.Series(index=df.index, dtype=float)
    sma = tr.rolling(length, min_periods=length).mean()
    if len(df) >= length:
        atr_series.iloc[length - 1] = sma.iloc[length - 1]
    for i in range(length, len(df)):
        atr_series.iloc[i] = alpha * tr.iloc[i] + (1 - alpha) * atr_series.iloc[i - 1]
    
    upperband = hl2 + multiplier * atr_series
    lowerband = hl2 - multiplier * atr_series
    
    direction = pd.Series(index=df.index, dtype=float)
    supertrend = pd.Series(index=df.index, dtype=float)
    
    for i in range(len(df)):
        if i == 0 or np.isnan(atr_series.iloc[i]):
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
            # Seed direction based on close vs hl2
            if close.iloc[i] >= hl2.iloc[i]:
                direction.iloc[i] = 1
                supertrend.iloc[i] = lowerband.iloc[i]
            else:
                direction.iloc[i] = -1
                supertrend.iloc[i] = upperband.iloc[i]
    
    return direction, supertrend

def find_entry_pattern_bars(df15: pd.DataFrame, entry_ts: pd.Timestamp, side: str, lookback_bars: int = 20):
    """
    Find the C0 (flip bar), C1 (alternating bar), C2 (entry bar) for a trade.
    Returns dict with bar indices and characteristics, or None if pattern not found.
    """
    try:
        entry_idx = df15.index.get_loc(entry_ts)
    except KeyError:
        return None
    
    if entry_idx < 2:  # Need at least 2 bars before entry
        return None
    
    # C2 is the entry bar
    c2_idx = entry_idx
    c2 = df15.iloc[c2_idx]
    c2_green = float(c2["Close"]) > float(c2["Open"])
    c2_body = abs(float(c2["Close"]) - float(c2["Open"]))
    c2_range = float(c2["High"]) - float(c2["Low"])
    
    # Look back to find C1 (alternating bar) and C0 (flip bar)
    # For LONG: C2 is green, C1 should be red, C0 should be green (flip to +1)
    # For SHORT: C2 is red, C1 should be green, C0 should be red (flip to -1)
    
    c1_idx = None
    c0_idx = None
    
    # Search backwards for alternating colored bar (C1)
    search_start = max(0, entry_idx - lookback_bars)
    for i in range(entry_idx - 1, search_start - 1, -1):
        bar = df15.iloc[i]
        bar_green = float(bar["Close"]) > float(bar["Open"])
        
        # C1 must be opposite color of C2
        if side == "long" and not bar_green and c2_green:
            c1_idx = i
            break
        elif side == "short" and bar_green and not c2_green:
            c1_idx = i
            break
    
    if c1_idx is None:
        return None
    
    # Search backwards from C1 for flip bar (C0)
    # C0 should match C2 color AND have a direction flip
    direction = df15["direction"]
    for i in range(c1_idx - 1, search_start - 1, -1):
        bar = df15.iloc[i]
        bar_green = float(bar["Close"]) > float(bar["Open"])
        
        # Check for direction flip and color match
        if i > 0:
            prev_dir = direction.iloc[i - 1]
            curr_dir = direction.iloc[i]
            if not np.isnan(prev_dir) and not np.isnan(curr_dir) and prev_dir != curr_dir:
                # Found a flip - check color matches expected pattern
                if side == "long" and bar_green and curr_dir == 1:
                    c0_idx = i
                    break
                elif side == "short" and not bar_green and curr_dir == -1:
                    c0_idx = i
                    break
    
    if c0_idx is None:
        return None
    
    # Extract characteristics
    c0 = df15.iloc[c0_idx]
    c1 = df15.iloc[c1_idx]
    
    return {
        "c0_idx": c0_idx,
        "c1_idx": c1_idx,
        "c2_idx": c2_idx,
        "c0": c0,
        "c1": c1,
        "c2": c2,
        "bars_to_entry": c2_idx - c0_idx,
    }

def extract_pattern_features(pattern_dict, atr_val: float):
    """Extract normalized features from entry pattern bars."""
    if pattern_dict is None or atr_val <= 0 or np.isnan(atr_val):
        return {}
    
    c0, c1, c2 = pattern_dict["c0"], pattern_dict["c1"], pattern_dict["c2"]
    
    def body_pct(bar):
        r = float(bar["High"]) - float(bar["Low"])
        return abs(float(bar["Close"]) - float(bar["Open"])) / r if r > 0 else 0
    
    def upper_wick_pct(bar):
        r = float(bar["High"]) - float(bar["Low"])
        return (float(bar["High"]) - max(float(bar["Open"]), float(bar["Close"]))) / r if r > 0 else 0
    
    def lower_wick_pct(bar):
        r = float(bar["High"]) - float(bar["Low"])
        return (min(float(bar["Open"]), float(bar["Close"])) - float(bar["Low"])) / r if r > 0 else 0
    
    def range_atr(bar, atr):
        return (float(bar["High"]) - float(bar["Low"])) / atr if atr > 0 else 0
    
    features = {
        # Flip bar (C0) features
        "flip_body_pct": body_pct(c0),
        "flip_upper_wick_pct": upper_wick_pct(c0),
        "flip_lower_wick_pct": lower_wick_pct(c0),
        "flip_range_atr": range_atr(c0, atr_val),
        
        # Alternating bar (C1) features
        "alt_body_pct": body_pct(c1),
        "alt_range_atr": range_atr(c1, atr_val),
        
        # Entry bar (C2) features
        "entry_body_pct": body_pct(c2),
        "entry_upper_wick_pct": upper_wick_pct(c2),
        "entry_lower_wick_pct": lower_wick_pct(c2),
        "entry_range_atr": range_atr(c2, atr_val),
        
        # Pattern timing
        "bars_to_entry": pattern_dict["bars_to_entry"],
    }
    
    return features

def extract_features_for_trades(trades_csv: str, ohlc_csv: str, out_parquet: str):
    """
    Extract enhanced features for ML from trades and OHLC data.
    Focus on entry bar context, directional encoding, recent bars before entry.
    
    CRITICAL: Strategy runs on 1-MINUTE data, not 15-minute!
    - SuperTrend calculated on 1m bars
    - Entry occurs at CLOSE of 1m entry bar
    - Initial stop is SuperTrend on that SAME 1m entry bar
    - EMA200 only filters which DAYS to trade (not entry signals)
    
    Therefore: Use 1-minute bars for features, NOT 15-minute resampled bars.
    """
    # Load trades
    trades = pd.read_csv(trades_csv)
    trades["entry_time"] = pd.to_datetime(trades["entry_time"], utc=True)
    trades["date"] = trades["entry_time"].dt.date
    trades["hour"] = trades["entry_time"].dt.hour
    trades["dow"] = trades["entry_time"].dt.dayofweek
    trades["label_win"] = (trades["pips"] > 0).astype(int)
    
    # Side encoding: long=1, short=-1
    trades["side_encoded"] = trades["side"].map({"long": 1, "short": -1})
    
    # Load 1-minute OHLC
    print("Loading 1-minute OHLC...")
    df1m = pd.read_csv(ohlc_csv)
    df1m["timestamp"] = pd.to_datetime(df1m["timestamp"], utc=True)
    df1m = df1m.set_index("timestamp").sort_index()
    
    # Compute ATR and SuperTrend on 1-MINUTE bars (matching the actual strategy)
    print("Computing ATR and SuperTrend on 1-minute data...")
    df1m["atr14"] = atr(df1m, period=14)
    df1m["direction"], df1m["supertrend"] = compute_supertrend_direction(df1m, length=10, multiplier=3.6)
    
    # Extract features for each trade
    print(f"Extracting features for {len(trades)} trades...")
    feature_rows = []
    
    for idx, trade in trades.iterrows():
        entry_ts = trade["entry_time"]
        side = trade["side"]
        
        # Get the ENTRY BAR (1-minute bar at entry_time)
        # Strategy enters at CLOSE of this bar, so all OHLC data from this bar is available
        if entry_ts not in df1m.index:
            continue  # Entry timestamp not in 1m data
        
        entry_bar = df1m.loc[entry_ts]
        
        atr_val = entry_bar["atr14"]
        if np.isnan(atr_val):
            # Backfill from prior bars
            prior_bars = df1m[df1m.index < entry_ts]
            if len(prior_bars) > 0:
                atr_series = prior_bars["atr14"].dropna()
                atr_val = atr_series.iloc[-1] if len(atr_series) > 0 else 0
            else:
                continue
        
        # Entry bar characteristics
        entry_high = float(entry_bar["High"])
        entry_low = float(entry_bar["Low"])
        entry_open = float(entry_bar["Open"])
        entry_close = float(entry_bar["Close"])
        entry_range = entry_high - entry_low
        
        if entry_range > 0:
            entry_body_pct = abs(entry_close - entry_open) / entry_range
            entry_upper_wick_pct = (entry_high - max(entry_open, entry_close)) / entry_range
            entry_lower_wick_pct = (min(entry_open, entry_close) - entry_low) / entry_range
        else:
            entry_body_pct = entry_upper_wick_pct = entry_lower_wick_pct = 0
        
        entry_range_atr = entry_range / atr_val if atr_val > 0 else 0
        
        # Previous bars context (look back 3 bars BEFORE entry bar)
        # Get prior bars for momentum calculation
        prior_bars = df1m[df1m.index < entry_ts]
        if len(prior_bars) >= 3:
            # Use last 3 bars before entry
            lookback_bars = prior_bars.iloc[-3:]
            avg_range_3bars = lookback_bars["High"].subtract(lookback_bars["Low"]).mean()
            avg_body_3bars = abs(lookback_bars["Close"] - lookback_bars["Open"]).mean()
            recent_range_atr = avg_range_3bars / atr_val if atr_val > 0 else 0
            recent_body_atr = avg_body_3bars / atr_val if atr_val > 0 else 0
            
            # Count directional bars in last 3
            green_bars = (lookback_bars["Close"] > lookback_bars["Open"]).sum()
            recent_momentum = green_bars / 3  # 0=all red, 0.33=1 green, 0.67=2 green, 1=all green
        else:
            recent_range_atr = recent_body_atr = recent_momentum = np.nan
        
        # Entry distance to stop (normalized by ATR)
        # Strategy enters at close of entry bar, initial stop is SuperTrend on same bar
        # Both entry price and initial stop are available at entry_time (no look-ahead)
        entry_price = trade.get("entry", np.nan)
        entry_close = float(entry_bar["Close"])
        supertrend_val = entry_bar.get("supertrend", np.nan)
        
        # Use actual entry price from trade (close of entry bar)
        # and SuperTrend from entry bar (initial stop, not trailed final_stop)
        if not np.isnan(entry_price) and not np.isnan(supertrend_val) and atr_val > 0:
            dist_to_stop = abs(entry_price - supertrend_val)
            entry_dist_stop_atr = dist_to_stop / atr_val
        else:
            entry_dist_stop_atr = np.nan
        
        # Directional interaction features
        # For long trades: lower wick is support (good), upper wick is resistance (bad)
        # For short trades: upper wick is resistance (good), lower wick is support (bad)
        side_enc = trade["side_encoded"]
        relevant_wick = entry_lower_wick_pct if side == "long" else entry_upper_wick_pct
        
        row = {
            # Basic context
            "hour": trade["hour"],
            "dow": trade["dow"],
            "side_encoded": side_enc,
            "atr14": atr_val,
            
            # Entry bar features
            "entry_body_pct": entry_body_pct,
            "entry_upper_wick_pct": entry_upper_wick_pct,
            "entry_lower_wick_pct": entry_lower_wick_pct,
            "entry_range_atr": entry_range_atr,
            "entry_dist_stop_atr": entry_dist_stop_atr,
            
            # Recent bars context
            "recent_range_atr": recent_range_atr,
            "recent_body_atr": recent_body_atr,
            "recent_momentum": recent_momentum,
            
            # Directional features (interactions)
            "relevant_wick": relevant_wick,  # The wick that matters for this direction
            "side_x_body": side_enc * entry_body_pct,  # Interaction: direction * body size
            "side_x_relevant_wick": side_enc * relevant_wick,
            
            # Labels
            "date": trade["date"],
            "pips": trade["pips"],
            "label_win": trade["label_win"],
        }
        
        feature_rows.append(row)
    
    # Create DataFrame
    df_features = pd.DataFrame(feature_rows)
    
    print(f"\n✅ Extracted features for {len(df_features)} / {len(trades)} trades")
    
    # Save to parquet
    Path(os.path.dirname(out_parquet)).mkdir(parents=True, exist_ok=True)
    df_features.to_parquet(out_parquet, index=False)
    
    # Save metadata
    feature_cols = [c for c in df_features.columns if c not in ["date", "pips", "label_win"]]
    meta = {
        "feature_columns": feature_cols,
        "n_features": len(feature_cols),
        "n_trades": len(df_features),
        "label": "label_win",
        "description": "Enhanced features v2: entry bar context from 1-MINUTE data (matching actual strategy). Entry price and initial stop both from same 1m entry bar (no look-ahead). Directional encoding, recent momentum, interaction terms.",
    }
    
    meta_path = out_parquet.replace(".parquet", "_meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    
    print(f"   Features saved: {out_parquet}")
    print(f"   Feature columns: {len(feature_cols)}")
    print(f"   Metadata: {meta_path}")
    
    return df_features

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades-csv", required=True, help="Path to trades CSV with entry_time, side, pips")
    ap.add_argument("--input-csv", required=True, help="Path to 1-minute OHLC CSV")
    ap.add_argument("--out-parquet", required=True, help="Output parquet path for features")
    args = ap.parse_args()
    
    extract_features_for_trades(args.trades_csv, args.input_csv, args.out_parquet)

if __name__ == "__main__":
    main()
