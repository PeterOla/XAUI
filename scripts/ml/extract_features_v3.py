"""
Enhanced feature extraction v3 - Comprehensive technical indicators and market microstructure.
Focus on finding predictive combinations through richer feature set.

New features:
- RSI (14, 30 period) - overbought/oversold
- MACD (12,26,9) - momentum divergence
- Bollinger Bands (20, 2std) - volatility and price position
- ATR percentile - volatility regime
- Volume (if available) - liquidity proxy
- Recent trend strength - sustained momentum
- Price distance from EMAs (20, 50, 200) - trend context
- Time since last trade - trade clustering
- Session effects - London/NY overlap
- Multi-timeframe features (1m, 5m, 15m aggregated)
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

def rsi(series: pd.Series, period: int = 14):
    """Calculate Relative Strength Index."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period, min_periods=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period, min_periods=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def macd(series: pd.Series, fast=12, slow=26, signal=9):
    """Calculate MACD indicator."""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def bollinger_bands(series: pd.Series, period=20, std_dev=2):
    """Calculate Bollinger Bands."""
    sma = series.rolling(period, min_periods=period).mean()
    std = series.rolling(period, min_periods=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    # Bollinger %B: where price is relative to bands (0=lower, 0.5=middle, 1=upper)
    bb_pct = (series - lower) / (upper - lower)
    # Bandwidth: normalized volatility
    bb_width = (upper - lower) / sma
    return upper, lower, bb_pct, bb_width

def ema(series: pd.Series, period: int):
    """Calculate Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()

def compute_supertrend_direction(df: pd.DataFrame, length: int = 10, multiplier: float = 3.6):
    """Compute SuperTrend direction (+1/-1) and SuperTrend level."""
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
            if close.iloc[i] >= hl2.iloc[i]:
                direction.iloc[i] = 1
                supertrend.iloc[i] = lowerband.iloc[i]
            else:
                direction.iloc[i] = -1
                supertrend.iloc[i] = upperband.iloc[i]
    
    return direction, supertrend

def extract_enhanced_features(trades_csv: str, ohlc_csv: str, out_parquet: str):
    """
    Extract comprehensive feature set for ML.
    """
    # Load trades
    trades = pd.read_csv(trades_csv)
    trades["entry_time"] = pd.to_datetime(trades["entry_time"], utc=True)
    trades["date"] = trades["entry_time"].dt.date
    trades["hour"] = trades["entry_time"].dt.hour
    trades["dow"] = trades["entry_time"].dt.dayofweek
    trades["label_win"] = (trades["pips"] > 0).astype(int)
    trades["side_encoded"] = trades["side"].map({"long": 1, "short": -1})
    
    # Load 1-minute OHLC
    print("Loading 1-minute OHLC...")
    df1m = pd.read_csv(ohlc_csv)
    df1m["timestamp"] = pd.to_datetime(df1m["timestamp"], utc=True)
    df1m = df1m.set_index("timestamp").sort_index()
    
    # Compute all indicators on 1-minute data
    print("Computing technical indicators on 1-minute data...")
    close = df1m["Close"]
    
    # ATR and SuperTrend
    df1m["atr14"] = atr(df1m, period=14)
    df1m["atr30"] = atr(df1m, period=30)
    df1m["direction"], df1m["supertrend"] = compute_supertrend_direction(df1m, length=10, multiplier=3.6)
    
    # RSI (multiple periods)
    df1m["rsi14"] = rsi(close, period=14)
    df1m["rsi30"] = rsi(close, period=30)
    
    # MACD
    df1m["macd"], df1m["macd_signal"], df1m["macd_hist"] = macd(close)
    
    # Bollinger Bands
    df1m["bb_upper"], df1m["bb_lower"], df1m["bb_pct"], df1m["bb_width"] = bollinger_bands(close, period=20)
    
    # EMAs for trend context
    df1m["ema20"] = ema(close, period=20)
    df1m["ema50"] = ema(close, period=50)
    df1m["ema200"] = ema(close, period=200)
    
    # ATR percentile (volatility regime)
    df1m["atr_pct"] = df1m["atr14"].rolling(100, min_periods=50).apply(
        lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min()) if x.max() > x.min() else 0.5, raw=False
    )
    
    # Recent momentum (3-bar, 10-bar)
    df1m["momentum_3"] = close.pct_change(3)
    df1m["momentum_10"] = close.pct_change(10)
    
    # Resample to 5-minute for multi-timeframe features
    print("Resampling to 5-minute for multi-timeframe features...")
    df5m = resample_ohlc(df1m, "5min")
    df5m["atr14_5m"] = atr(df5m, period=14)
    df5m["rsi14_5m"] = rsi(df5m["Close"], period=14)
    df5m["close_5m"] = df5m["Close"]
    
    # Extract features for each trade
    print(f"Extracting features for {len(trades)} trades...")
    feature_rows = []
    
    last_trade_time = None
    
    for idx, trade in trades.iterrows():
        entry_ts = trade["entry_time"]
        side = trade["side"]
        
        # Get entry bar (1-minute)
        if entry_ts not in df1m.index:
            continue
        
        entry_bar = df1m.loc[entry_ts]
        
        # Basic bar features
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
        
        # ATR features
        atr_val = entry_bar["atr14"]
        if np.isnan(atr_val):
            prior_bars = df1m[df1m.index < entry_ts]
            if len(prior_bars) > 0:
                atr_series = prior_bars["atr14"].dropna()
                atr_val = atr_series.iloc[-1] if len(atr_series) > 0 else 0
            else:
                continue
        
        entry_range_atr = entry_range / atr_val if atr_val > 0 else 0
        
        # SuperTrend distance
        supertrend_val = entry_bar.get("supertrend", np.nan)
        if not np.isnan(supertrend_val) and atr_val > 0:
            entry_dist_stop_atr = abs(entry_close - supertrend_val) / atr_val
        else:
            entry_dist_stop_atr = np.nan
        
        # Technical indicators
        rsi14_val = entry_bar.get("rsi14", np.nan)
        rsi30_val = entry_bar.get("rsi30", np.nan)
        macd_hist_val = entry_bar.get("macd_hist", np.nan)
        bb_pct_val = entry_bar.get("bb_pct", np.nan)
        bb_width_val = entry_bar.get("bb_width", np.nan)
        atr_pct_val = entry_bar.get("atr_pct", np.nan)
        momentum_3_val = entry_bar.get("momentum_3", np.nan)
        momentum_10_val = entry_bar.get("momentum_10", np.nan)
        
        # Distance from EMAs (normalized by ATR)
        ema20_val = entry_bar.get("ema20", np.nan)
        ema50_val = entry_bar.get("ema50", np.nan)
        ema200_val = entry_bar.get("ema200", np.nan)
        
        dist_ema20_atr = abs(entry_close - ema20_val) / atr_val if not np.isnan(ema20_val) and atr_val > 0 else np.nan
        dist_ema50_atr = abs(entry_close - ema50_val) / atr_val if not np.isnan(ema50_val) and atr_val > 0 else np.nan
        dist_ema200_atr = abs(entry_close - ema200_val) / atr_val if not np.isnan(ema200_val) and atr_val > 0 else np.nan
        
        # Price position relative to EMAs (above=1, below=-1)
        above_ema20 = 1 if entry_close > ema20_val else -1 if not np.isnan(ema20_val) else 0
        above_ema50 = 1 if entry_close > ema50_val else -1 if not np.isnan(ema50_val) else 0
        above_ema200 = 1 if entry_close > ema200_val else -1 if not np.isnan(ema200_val) else 0
        
        # Recent bars context (last 3 bars before entry)
        prior_bars = df1m[df1m.index < entry_ts]
        if len(prior_bars) >= 3:
            lookback_bars = prior_bars.iloc[-3:]
            avg_range_3bars = lookback_bars["High"].subtract(lookback_bars["Low"]).mean()
            avg_body_3bars = abs(lookback_bars["Close"] - lookback_bars["Open"]).mean()
            recent_range_atr = avg_range_3bars / atr_val if atr_val > 0 else 0
            recent_body_atr = avg_body_3bars / atr_val if atr_val > 0 else 0
            
            green_bars = (lookback_bars["Close"] > lookback_bars["Open"]).sum()
            recent_momentum = green_bars / 3
        else:
            recent_range_atr = recent_body_atr = recent_momentum = np.nan
        
        # 5-minute timeframe features
        # Find the last completed 5m bar before entry
        df5m_prior = df5m[df5m.index < entry_ts]
        if len(df5m_prior) > 0:
            bar_5m = df5m_prior.iloc[-1]
            atr14_5m_val = bar_5m.get("atr14_5m", np.nan)
            rsi14_5m_val = bar_5m.get("rsi14_5m", np.nan)
        else:
            atr14_5m_val = rsi14_5m_val = np.nan
        
        # Time since last trade (trade clustering)
        if last_trade_time is not None:
            minutes_since_last = (entry_ts - last_trade_time).total_seconds() / 60
        else:
            minutes_since_last = np.nan
        last_trade_time = entry_ts
        
        # Session indicators
        # London: 8-16 UTC, NY: 13-21 UTC, Overlap: 13-16 UTC
        is_london = 1 if 8 <= trade["hour"] < 16 else 0
        is_ny = 1 if 13 <= trade["hour"] < 21 else 0
        is_overlap = 1 if 13 <= trade["hour"] < 16 else 0
        
        # Directional features
        side_enc = trade["side_encoded"]
        relevant_wick = entry_lower_wick_pct if side == "long" else entry_upper_wick_pct
        
        # Interaction features
        side_x_body = side_enc * entry_body_pct
        side_x_relevant_wick = side_enc * relevant_wick
        side_x_rsi = side_enc * rsi14_val if not np.isnan(rsi14_val) else np.nan
        side_x_macd = side_enc * macd_hist_val if not np.isnan(macd_hist_val) else np.nan
        
        row = {
            # Basic context
            "hour": trade["hour"],
            "dow": trade["dow"],
            "side_encoded": side_enc,
            
            # Session indicators
            "is_london": is_london,
            "is_ny": is_ny,
            "is_overlap": is_overlap,
            
            # Entry bar basic features
            "entry_body_pct": entry_body_pct,
            "entry_upper_wick_pct": entry_upper_wick_pct,
            "entry_lower_wick_pct": entry_lower_wick_pct,
            "entry_range_atr": entry_range_atr,
            "entry_dist_stop_atr": entry_dist_stop_atr,
            
            # ATR features
            "atr14": atr_val,
            "atr_pct": atr_pct_val,  # Volatility regime
            
            # Technical indicators (1m)
            "rsi14": rsi14_val,
            "rsi30": rsi30_val,
            "macd_hist": macd_hist_val,
            "bb_pct": bb_pct_val,  # Bollinger %B
            "bb_width": bb_width_val,  # Bollinger bandwidth
            "momentum_3": momentum_3_val,
            "momentum_10": momentum_10_val,
            
            # EMA distance features
            "dist_ema20_atr": dist_ema20_atr,
            "dist_ema50_atr": dist_ema50_atr,
            "dist_ema200_atr": dist_ema200_atr,
            "above_ema20": above_ema20,
            "above_ema50": above_ema50,
            "above_ema200": above_ema200,
            
            # Recent bars context
            "recent_range_atr": recent_range_atr,
            "recent_body_atr": recent_body_atr,
            "recent_momentum": recent_momentum,
            
            # Multi-timeframe (5m)
            "atr14_5m": atr14_5m_val,
            "rsi14_5m": rsi14_5m_val,
            
            # Trade clustering
            "minutes_since_last": minutes_since_last,
            
            # Directional features
            "relevant_wick": relevant_wick,
            "side_x_body": side_x_body,
            "side_x_relevant_wick": side_x_relevant_wick,
            "side_x_rsi": side_x_rsi,
            "side_x_macd": side_x_macd,
            
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
        "description": "Enhanced features v3: RSI, MACD, Bollinger Bands, EMA distances, volatility regime, momentum, multi-timeframe, session effects, interaction terms",
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
    
    extract_enhanced_features(args.trades_csv, args.input_csv, args.out_parquet)

if __name__ == "__main__":
    main()
