"""
Clean reimplementation of the Twelve Data base strategy with plotting and README-conformant rules.
"""

import os
import sys
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
 


@dataclass
class StrategyConfig:
    st_length: int = 10
    st_multiplier: float = 3.6
    max_sl_distance_pips: float = 520.0  # cap between entry and ST in pips
    pip_size: float = 0.01  # XAUUSD pip definition (0.01 USD = 1 pip) — fixed, not exposed via CLI
    entry_hours: Optional[Tuple[int, int]] = (13, 16)  # inclusive start, exclusive end (UTC)
    filter_days: Optional[set] = None  # set of allowed dates (datetime.date)
    allowed_sides: Optional[set] = None  # {"long","short"} or None for both

# Default output directory for results and plots (store run outputs under results/trends by default)
DEFAULT_OUT_DIR = os.path.join("results", "trends")

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
    """Compute SuperTrend direction (+1/-1) and line using an ATR based on RMA.

    Returns (direction, supertrend).
    """
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    close = df["Close"].astype(float)

    hl2 = (high + low) / 2.0
    # True Range without NaN propagation from shift
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
            # Seed direction based on where close sits relative to hl2
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


def backtest_supertrend(df: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    """Backtest implementing README rules:
    - Valid trade days filter (optional)
    - Entry pattern: flip, then alternating candle, then enter on following candle (if still within hours)
    - Enforce entry hours and max SL distance cap at activation
    - Exit when Low<=ST (long) or High>=ST (short); trail SL to current ST each bar
    """
    if df.empty:
        return pd.DataFrame(columns=["entry_time", "exit_time", "side", "entry", "exit", "final_stop", "pips"])

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df.set_index("timestamp", inplace=True)
    df = df.sort_index()

    if cfg.filter_days:
        mask = pd.Series([ts.date() in cfg.filter_days for ts in df.index], index=df.index)
        df = df[mask]
        if df.empty:
            return pd.DataFrame(columns=["entry_time", "exit_time", "side", "entry", "exit", "final_stop", "pips"]) 

    direction, st = compute_supertrend(df, cfg.st_length, cfg.st_multiplier)
    df["direction"] = direction
    df["supertrend"] = st

    trades = []
    position: Optional[Tuple[str, pd.Timestamp, float, float]] = None  # (side, entry_time, entry_price, stop_price)
    pending_entry: Optional[dict] = None  # {"entry_idx": Timestamp, "side": "long"|"short"}
    direction_prev: Optional[float] = None
    prev_supertrend: Optional[float] = None

    def pips_between(a: float, b: float) -> float:
        return abs(float(a) - float(b)) / cfg.pip_size

    idx = list(df.index)
    n = len(idx)
    for i in range(1, n):
        ts = idx[i]
        # derive current direction and supertrend with carry-forward of prior ST
        current_direction = df.iloc[i]["direction"]
        prior_supertrend = prev_supertrend
        st_raw = df.iloc[i]["supertrend"]
        supertrend = float(st_raw) if not np.isnan(st_raw) else (float(prior_supertrend) if prior_supertrend is not None else np.nan)

        # 1) Activate pending entry on its bar, honoring hours and cap
        if pending_entry is not None and ts >= pending_entry["entry_idx"]:
            if within_entry_hours(ts, cfg.entry_hours) and position is None:
                st_now = df.loc[ts, "supertrend"]
                if not np.isnan(st_now):
                    entry_price = float(df.loc[ts, "Close"])  # enter at close of entry bar
                    if pips_between(entry_price, st_now) <= cfg.max_sl_distance_pips:
                        position = (pending_entry["side"], ts, entry_price, float(st_now))
            pending_entry = None

        # 2) Manage open position: trail and check exit via H/L cross of stop
        if position is not None:
            side, ent_time, ent_price, sl_price = position
            # trailing supertrend: prefer current ST; if trend changed away from side, stick to prior ST
            trail_st = supertrend if not np.isnan(supertrend) else prior_supertrend
            if side == "long" and current_direction != 1:
                trail_st = prior_supertrend
            elif side == "short" and current_direction != -1:
                trail_st = prior_supertrend

            # Trail SL toward price using trail ST
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
                # Prefer previous candle's ST to avoid exits at post-flip jumps
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
                })
                position = None
            else:
                position = (side, ent_time, ent_price, sl_price)

        # 3) Only schedule new entries during entry hours and if nothing is pending
        if not within_entry_hours(ts, cfg.entry_hours) or pending_entry is not None:
            # carry forward state even if we skip scheduling new entries
            direction_prev = current_direction
            prev_supertrend = supertrend if not np.isnan(supertrend) else prior_supertrend
            continue

        prev_dir = df.iloc[i - 1]["direction"]
        curr_dir = current_direction
        if np.isnan(prev_dir) or np.isnan(curr_dir) or prev_dir == curr_dir:
            # carry forward state
            direction_prev = current_direction
            prev_supertrend = supertrend if not np.isnan(supertrend) else prior_supertrend
            continue  # no flip

        curr_open = float(df.iloc[i]["Open"])
        curr_close = float(df.iloc[i]["Close"])
        flip_bull = prev_dir == -1 and curr_dir == 1
        flip_bear = prev_dir == 1 and curr_dir == -1

        # C0 color must align with flip
        C0_green = curr_close > curr_open
        C0_red = curr_close < curr_open

        if flip_bull and C0_green:
            # find next red after C0, then enter on following bar if it's green
            if i + 1 >= n:
                direction_prev = current_direction
                prev_supertrend = supertrend if not np.isnan(supertrend) else prior_supertrend
                continue
            future = df.iloc[i + 1 :]
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
                    # Respect allowed sides
                    if cfg.allowed_sides is None or "long" in cfg.allowed_sides:
                        pending_entry = {"entry_idx": df.index[enter_pos], "side": "long"}

        elif flip_bear and C0_red:
            # find next green after C0, then enter on following bar if it's red
            if i + 1 >= n:
                direction_prev = current_direction
                prev_supertrend = supertrend if not np.isnan(supertrend) else prior_supertrend
                continue
            future = df.iloc[i + 1 :]
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
                    # Respect allowed sides
                    if cfg.allowed_sides is None or "short" in cfg.allowed_sides:
                        pending_entry = {"entry_idx": df.index[enter_pos], "side": "short"}

        # carry forward state for next iteration
        direction_prev = current_direction
        prev_supertrend = supertrend if not np.isnan(supertrend) else prior_supertrend

    return pd.DataFrame(trades)


def plot_supertrend(
    df: pd.DataFrame,
    results: pd.DataFrame,
    out_html: str,
    title: Optional[str] = None,
    cap_pips: Optional[float] = None,
    entry_hours: Optional[Tuple[int, int]] = None,
    pip_size: float = 0.01,
    lite: bool = False,
) -> None:
    dfi = df.copy()
    dfi["timestamp"] = pd.to_datetime(dfi["timestamp"], utc=True)
    dfi.set_index("timestamp", inplace=True)
    dfi = dfi.sort_index()

    PIP_FACTOR = 1.0 / pip_size
    if not lite:
        dfi["body_pips"] = (dfi["Close"] - dfi["Open"]).abs() * PIP_FACTOR
        tr1 = (dfi["High"] - dfi["Low"]).abs()
        tr2 = (dfi["High"] - dfi["Close"].shift(1)).abs()
        tr3 = (dfi["Low"] - dfi["Close"].shift(1)).abs()
        dfi["true_range"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr_period = 14
        dfi["atr_pips"] = dfi["true_range"].rolling(window=atr_period).mean() * PIP_FACTOR

    flips = dfi.get("direction")
    if flips is not None:
        flips = flips.ne(flips.shift(1)).fillna(False)
    else:
        flips = pd.Series(False, index=dfi.index)

    if entry_hours is None:
        in_window = pd.Series(True, index=dfi.index)
    else:
        h0, h1 = entry_hours
        in_window = pd.Series([(h0 <= t.hour < h1) for t in dfi.index], index=dfi.index)

    if lite:
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True)
    else:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.72, 0.28])

    st_series = dfi.get("supertrend", pd.Series([np.nan] * len(dfi), index=dfi.index))
    fig.add_trace(
        go.Candlestick(
            x=dfi.index,
            open=dfi["Open"], high=dfi["High"], low=dfi["Low"], close=dfi["Close"], name="XAUUSD",
            increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
            increasing_fillcolor="#26a69a", decreasing_fillcolor="#ef5350",
            showlegend=False,
            hovertext=None if lite else [
                (
                    f"{ts:%Y-%m-%d %H:%M} UTC\n"
                    f"O:{o:.2f} H:{h:.2f} L:{l:.2f} C:{c:.2f}\n"
                    + (f"ST:{st:.2f} | Dist:{((c-st)*PIP_FACTOR):+.1f} pips\n" if not pd.isna(st) else "ST:n/a\n")
                    + (f"Body:{body:.1f} pips | ATR:{atr:.1f} pips\n" if not (pd.isna(body) or pd.isna(atr)) else "")
                    + ("Flip:yes\n" if fl else "Flip:no\n")
                    + ("InWindow:yes" if iw else "InWindow:no")
                )
                for ts, o, h, l, c, st, body, atr, fl, iw in zip(
                    dfi.index,
                    dfi["Open"], dfi["High"], dfi["Low"], dfi["Close"],
                    st_series,
                    (dfi["body_pips"] if not lite else [np.nan]*len(dfi)),
                    (dfi["atr_pips"] if not lite else [np.nan]*len(dfi)),
                    flips, in_window,
                )
            ],
            hoverinfo="none" if lite else "text",
        ), row=1, col=1,
    )

    if "supertrend" in dfi.columns:
        fig.add_trace(
            go.Scatter(x=dfi.index, y=dfi["supertrend"], mode="lines", name="SuperTrend", line=dict(color="#ffb74d", width=1.4)),
            row=1, col=1,
        )

    if not results.empty:
        fig.add_trace(
            go.Scatter(
                x=pd.to_datetime(results["entry_time"], utc=True), y=results["entry"],
                mode="markers", name="Entry",
                marker=dict(color=["#00e676" if s == "long" else "#ff5252" for s in results["side"]],
                            symbol=["triangle-up" if s == "long" else "triangle-down" for s in results["side"]],
                            size=12, line=dict(width=1, color="#1b5e20")),
            ), row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=pd.to_datetime(results["exit_time"], utc=True), y=results["exit"],
                mode="markers", name="Exit",
                marker=dict(color="#fafafa", symbol="x", size=10, line=dict(width=1, color="#424242")),
            ), row=1, col=1,
        )

    if not lite and "supertrend" in dfi.columns:
        dist_signed = (dfi["Close"] - dfi["supertrend"]) * PIP_FACTOR
        dist_abs = dist_signed.abs()
        fig.add_trace(go.Scatter(x=dfi.index, y=dist_signed, mode="lines", name="Dist to ST (pips)", line=dict(color="#64b5f6", width=1.5)), row=2, col=1)
        fig.add_trace(go.Scatter(x=dfi.index, y=dist_abs, mode="lines", name="|Dist| (pips)", line=dict(color="#b0bec5", width=1, dash="dot")), row=2, col=1)
        if cap_pips is not None:
            fig.add_trace(go.Scatter(x=dfi.index, y=pd.Series(cap_pips, index=dfi.index), mode="lines", name="Cap (pips)", line=dict(color="#ffb74d", width=1, dash="dash")), row=2, col=1)

    buttons = [dict(label="All", method="relayout", args=[{"xaxis.autorange": True, "yaxis.autorange": True}])]
    if not results.empty:
        pad = pd.Timedelta(minutes=30)
        min_idx, max_idx = dfi.index.min(), dfi.index.max()
        for i, r in enumerate(results.itertuples(), start=1):
            start = max(min_idx, pd.to_datetime(r.entry_time, utc=True) - pad)
            end = min(max_idx, pd.to_datetime(r.exit_time, utc=True) + pad if hasattr(r, 'exit_time') and pd.notna(r.exit_time) else pd.to_datetime(r.entry_time, utc=True) + pad)
            window = dfi.loc[start:end]
            if window.empty:
                continue
            price_min = np.nanmin([window["Low"].min(), window["supertrend"].min() if "supertrend" in window.columns else window["Low"].min()])
            price_max = np.nanmax([window["High"].max(), window["supertrend"].max() if "supertrend" in window.columns else window["High"].max()])
            if np.isnan(price_min) or np.isnan(price_max):
                continue
            pad_y = max(0.5, (price_max - price_min) * 0.05) if not np.isclose(price_min, price_max) else max(0.5, abs(price_min) * 0.001)
            buttons.append(dict(label=f"Trade {i}", method="relayout", args=[{"xaxis.range": [start, end], "yaxis.range": [price_min - pad_y, price_max + pad_y]}]))

    fig.update_layout(
        title=title or "SuperTrend Backtest",
        template="plotly_dark",
        hovermode="x unified",
        dragmode="pan",
        plot_bgcolor="#111827",
        paper_bgcolor="#111827",
        font=dict(color="#e5e7eb"),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=30, t=60, b=40),
        updatemenus=None if lite else [dict(type="dropdown", direction="down", buttons=buttons, showactive=True, x=0, y=1.1, xanchor="left", yanchor="top")],
    )
    if not lite:
        fig.update_yaxes(title_text="Dist to ST (pips)", row=2, col=1)

    os.makedirs(os.path.dirname(out_html), exist_ok=True)
    config = {"scrollZoom": True, "displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}
    fig.write_html(out_html, config=config)


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="Minimal SuperTrend strategy using XAUUSD CSVs.")
    # Default input CSV candidates (prefer user's absolute path, then relative fallbacks)
    default_input_candidates = [
        r"C:\\Users\\Olale\\Documents\\Codebase\\Quant\\XAUI\\data\\twelvedata_xauusd_1min_full.csv",
        os.path.join("data", "twelvedata_xauusd_1min_full.csv"),
        os.path.join("data", "combined_xauusd_1min_full.csv"),
    ]
    default_input_csv = next((p for p in default_input_candidates if os.path.exists(p)), default_input_candidates[0])
    parser.add_argument(
        "--input-csv",
        required=False,
        default=default_input_csv,
        help=f"Path to CSV under data/ (default: {default_input_csv})",
    )
    parser.add_argument("--st-length", type=int, default=10)
    parser.add_argument("--st-multiplier", type=float, default=3.6)
    parser.add_argument("--max-sl-distance-pips", type=float, default=520.0)
    parser.add_argument("--entry-hours", default="13-16", help="UTC hour window, e.g., 13-16; or 'all'")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help=f"Base output directory (default: {DEFAULT_OUT_DIR}); timeframe subfolder will be appended if using --timeframe")
    parser.add_argument("--timeframe", default="1m", help="Timeframe label for output subfolder (e.g. 1m,5m,15m). Default: 1m")
    parser.add_argument("--plot", action="store_true", help="Save an interactive HTML plot alongside results")
    parser.add_argument("--plot-lite", action="store_true", help="Faster plot: single panel, minimal hover, no distance metrics")
    parser.add_argument("--plot-latest-only", action="store_true", help="Only write latest.html (skip named plot_<tag>.html)")
    parser.add_argument(
        "--plot-html",
        default=None,
        help="Optional explicit HTML output path for the plot; defaults to results folder",
    )
    parser.add_argument("--filter-csv", default=None, help="Optional CSV with a 'timestamp' column; only dates present are tradable")
    parser.add_argument("--no-trend-filter", action="store_true", help="Disable the default EMA200 per-day Up trend filter (if present)")
    parser.add_argument("--max-rows", type=int, default=None, help="Optional: limit number of rows read from input for a fast smoke test")
    parser.add_argument("--trend", choices=["up", "down", "both"], default="up", help="Which trend to trade when using the EMA200 trend file (default: up)")
    parser.add_argument("--trend-tfs", default=None, help="Comma-separated list of timeframe trend files to require simultaneously (e.g., '1m,5m,15m'). Uses intersection of allowed days.")
    parser.add_argument("--long-only", action="store_true", help="Only take long trades (default behavior if no side is specified)")
    parser.add_argument("--short-only", action="store_true", help="Only take short trades")
    parser.add_argument("--run-tag", default="", help="Optional tag appended to output filenames (e.g., 'up_buy_only')")
    parser.add_argument("--date-start", default=None, help="Optional start date (UTC, YYYY-MM-DD) to filter input rows")
    parser.add_argument("--date-end", default=None, help="Optional end date (UTC, YYYY-MM-DD, inclusive) to filter input rows")
    
    args = parser.parse_args(argv)

    if args.entry_hours.lower() == "all":
        entry_hours = None
    else:
        try:
            h0, h1 = args.entry_hours.split("-")
            entry_hours = (int(h0), int(h1))
        except Exception:
            raise SystemExit("Invalid --entry-hours. Use 'all' or 'HH-HH' like 13-16.")

    if not os.path.exists(args.input_csv):
        raise SystemExit(f"Input CSV not found: {args.input_csv}. Provide --input-csv or ensure the default exists.")
    print(f"Using input CSV: {args.input_csv}")
    df = pd.read_csv(args.input_csv)
    # Date range filtering (applied before any other filtering)
    if args.date_start or args.date_end:
        try:
            ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
            mask = pd.Series(True, index=df.index)
            if args.date_start:
                start_ts = pd.to_datetime(args.date_start).tz_localize("UTC") if pd.to_datetime(args.date_start).tzinfo is None else pd.to_datetime(args.date_start).tz_convert("UTC")
                mask &= ts >= start_ts
            if args.date_end:
                # inclusive end: add 1 day and use <
                end_ts = pd.to_datetime(args.date_end)
                if end_ts.tzinfo is None:
                    end_ts = end_ts.tz_localize("UTC")
                else:
                    end_ts = end_ts.tz_convert("UTC")
                end_excl = end_ts + pd.Timedelta(days=1)
                mask &= ts < end_excl
            before = len(df)
            df = df.loc[mask].copy()
            print(f"Date filter applied: {args.date_start or '-'} to {args.date_end or '-'} — {before} -> {len(df)} rows")
        except Exception as e:
            print(f"⚠️ Failed to apply date filter: {e}")
    if args.max_rows is not None and args.max_rows > 0:
        df = df.head(args.max_rows)
        print(f"Limiting to first {len(df)} rows for quick test (--max-rows)")

    # optional filter days
    filter_days = None
    if args.filter_csv:
        try:
            fdf = pd.read_csv(args.filter_csv)
            # Support two kinds of filter CSVs:
            # 1) a list of timestamps (column 'timestamp') -> use those dates
            # 2) an ema/day trend file with columns ['date','trend'] -> allow only dates where trend == 'Up'
            if "trend" in fdf.columns and ("date" in fdf.columns or "Date" in fdf.columns):
                date_col = "date" if "date" in fdf.columns else "Date"
                # parse dates (assume ISO-like YYYY-MM-DD or similar)
                ts = pd.to_datetime(fdf[date_col], utc=True, errors="coerce").dt.date
                ups = fdf["trend"].astype(str).str.strip().str.lower() == "up"
                filter_days = set(ts[ups].dropna().unique().tolist())
                print(f"Loaded trend filter from {args.filter_csv}: {len(filter_days)} Up days")
            elif "timestamp" in fdf.columns:
                ts = pd.to_datetime(fdf["timestamp"], utc=True, errors="coerce")
                filter_days = set(ts.dt.date.dropna().unique().tolist())
                print(f"Loaded date filter from {args.filter_csv}: {len(filter_days)} unique dates")
            else:
                # Try to detect a date-like column (e.g., 'date')
                candidates = [c for c in fdf.columns if c.lower() == "date"]
                if candidates:
                    ts = pd.to_datetime(fdf[candidates[0]], utc=True, errors="coerce")
                    filter_days = set(ts.dt.date.dropna().unique().tolist())
                    print(f"Loaded date filter from {args.filter_csv}: {len(filter_days)} unique dates (from column {candidates[0]})")
                else:
                    print(f"⚠️ Filter CSV {args.filter_csv} did not contain 'trend' or 'timestamp'/'date' columns; ignoring filter.")
        except Exception as e:
            print(f"⚠️ Failed to load filter CSV {args.filter_csv}: {e}")

    # Build filter_days from trend files if not explicitly provided
    if filter_days is None and not args.no_trend_filter:
        def load_days_from_tf(tf_label: str) -> Optional[set]:
            tf_label = tf_label.strip().lower()
            tf_file = os.path.join("data", "trend", f"ema200_trend_by_date_{tf_label}.csv")
            if not os.path.exists(tf_file):
                print(f"⚠️ Trend file not found for timeframe '{tf_label}': {tf_file}")
                return None
            try:
                fdf = pd.read_csv(tf_file)
                date_col = "date" if "date" in fdf.columns else ("Date" if "Date" in fdf.columns else None)
                if not date_col or "trend" not in fdf.columns:
                    print(f"⚠️ Trend file missing columns (date/trend): {tf_file}")
                    return None
                ts = pd.to_datetime(fdf[date_col], utc=True, errors="coerce").dt.date
                tvals = fdf["trend"].astype(str).str.strip().str.lower()
                if args.trend == "up":
                    sel = tvals == "up"
                elif args.trend == "down":
                    sel = tvals == "down"
                else:
                    sel = pd.Series(True, index=tvals.index)
                return set(ts[sel].dropna().unique().tolist())
            except Exception as e:
                print(f"⚠️ Failed loading trend file {tf_file}: {e}")
                return None

        if args.trend_tfs:
            tf_list = [s for s in args.trend_tfs.split(',') if s.strip()]
            sets = []
            for tf_label in tf_list:
                s = load_days_from_tf(tf_label)
                if s is None:
                    print(f"⚠️ Skipping timeframe '{tf_label}' due to missing/invalid file.")
                    continue
                print(f"Loaded trend days ({args.trend}) from {tf_label}: {len(s)} days")
                sets.append(s)
            if sets:
                inter = sets[0].copy()
                for s in sets[1:]:
                    inter &= s
                filter_days = inter
                print(f"Combined trend filter (ALL of {','.join(tf_list)}) => {len(filter_days)} days")
            else:
                print("No valid trend files loaded for --trend-tfs; no default date filter applied")
        else:
            # Single timeframe behavior (backward compatible): use --timeframe, fallback to 1m
            tf = (args.timeframe or "1m").strip().lower()
            s = load_days_from_tf(tf)
            if s is None:
                s = load_days_from_tf("1m")
            if s is not None:
                filter_days = s
                print(f"Default trend filter loaded for {tf}: {len(filter_days)} {args.trend} days")
            else:
                print("No default trend file found; no default date filter applied")

    # Sides filtering
    if args.long_only and args.short_only:
        raise SystemExit("--long-only and --short-only cannot be used together")
    # Default to long-only when neither flag is provided (up_buy_only default)
    if not args.long_only and not args.short_only:
        allowed_sides = {"long"}
    elif args.long_only:
        allowed_sides = {"long"}
    elif args.short_only:
        allowed_sides = {"short"}
    else:
        allowed_sides = None

    cfg = StrategyConfig(
        st_length=args.st_length,
        st_multiplier=args.st_multiplier,
        max_sl_distance_pips=args.max_sl_distance_pips,
        entry_hours=entry_hours,
        filter_days=filter_days,
        allowed_sides=allowed_sides,
    )

    results = backtest_supertrend(df, cfg)

    # Derive final output directory: append timeframe subfolder if user kept the default base out-dir or if they requested it explicitly.
    final_out_dir = args.out_dir
    # If combining multiple trend TFs, store under a combo folder; else use timeframe folder
    combo_label = None
    if args.trend_tfs:
        tf_list = sorted([s.strip().lower() for s in args.trend_tfs.split(',') if s.strip()])
        combo_label = f"combo_{'_'.join(tf_list)}"
        final_out_dir = os.path.join(final_out_dir, combo_label)
    elif args.timeframe and args.timeframe.strip():
        tf = args.timeframe.strip()
        if not final_out_dir.endswith(tf):
            final_out_dir = os.path.join(final_out_dir, tf)
    os.makedirs(final_out_dir, exist_ok=True)

    base = os.path.splitext(os.path.basename(args.input_csv))[0]
    # If user did not provide a run tag and defaults imply Up + Long-only, set a helpful default tag
    implied_up = (args.trend == "up")
    implied_long_only = (allowed_sides == {"long"})
    auto_tag = "up_buy_only" if (implied_up and implied_long_only) else ""
    tag = f"_{args.run_tag}" if args.run_tag else (f"_{auto_tag}" if auto_tag else "")
    # New naming convention inside timeframe folder: trades(.csv), trades_simple(.csv), plot.html
    trades_filename = f"trades{tag}.csv" if tag else "trades.csv"
    out_csv = os.path.join(final_out_dir, trades_filename)
    results.to_csv(out_csv, index=False)

    # Enhanced post-backtest summary (prints detailed performance and saves a compact CSV)
    print(f"✅ Backtest complete — {len(results)} trades executed.")
    if not results.empty:
        try:
            # Show a quick sample and total pips
            print(results.head())
            print(f"Total Pips: {results['pips'].sum():.1f}")

            # Performance summary
            total_trades = len(results)
            wins = (results['pips'] > 0).sum()
            losses = (results['pips'] < 0).sum()
            win_rate = wins / total_trades if total_trades else 0.0
            avg_trade = results['pips'].mean()
            avg_win = results.loc[results['pips'] > 0, 'pips'].mean()
            avg_loss = results.loc[results['pips'] < 0, 'pips'].mean()
            best_trade = results['pips'].max()
            worst_trade = results['pips'].min()
            gross_gain = results.loc[results['pips'] > 0, 'pips'].sum()
            gross_loss = results.loc[results['pips'] < 0, 'pips'].sum()
            profit_factor = gross_gain / abs(gross_loss) if gross_loss != 0 else float('inf')

            results['equity'] = results['pips'].cumsum()
            running_max = results['equity'].cummax()
            drawdowns = results['equity'] - running_max
            max_drawdown = drawdowns.min()

            print("\nPerformance Summary:")
            print(f"- Total trades: {total_trades}")
            print(f"- Win rate: {win_rate:.2%}")
            print(f"- Average trade: {avg_trade:.1f} pips")
            print(f"- Average win: {avg_win:.1f} pips")
            print(f"- Average loss: {avg_loss:.1f} pips")
            print(f"- Best trade: {best_trade:.1f} pips")
            print(f"- Worst trade: {worst_trade:.1f} pips")
            print(f"- Profit factor: {profit_factor:.2f}")
            print(f"- Max drawdown: {max_drawdown:.1f} pips")

            # Sharpe ratio (per-trade) and an approximate annualized Sharpe
            try:
                std_trade = results['pips'].std(ddof=1)
                if std_trade and std_trade > 0:
                    sharpe_per_trade = avg_trade / std_trade
                    # Approx annualized: scale by sqrt(trades per year)
                    first_t = pd.to_datetime(results['entry_time'].iloc[0], utc=True)
                    last_t = pd.to_datetime(results['entry_time'].iloc[-1], utc=True)
                    years = max((last_t - first_t).days / 365.25, 1e-9)
                    trades_per_year = total_trades / years if years > 0 else float('nan')
                    sharpe_annual = sharpe_per_trade * np.sqrt(trades_per_year) if trades_per_year and trades_per_year > 0 else float('nan')
                    print(f"- Sharpe (per-trade): {sharpe_per_trade:.2f}")
                    if np.isfinite(sharpe_annual):
                        print(f"- Sharpe (annualized ~): {sharpe_annual:.2f}  # approx via sqrt(trades/year)")
                else:
                    print("- Sharpe: n/a (zero variance)")
            except Exception as _:
                print("- Sharpe: n/a (calc error)")

        except Exception as e:
            print(f"⚠️ Failed to compute performance summary: {e}")

        # Simplified results CSV (timestamp, pips, final_stop, optional side)
        try:
            cols = ["entry_time", "pips", "final_stop"]
            if "side" in results.columns:
                cols.append("side")
            available_cols = [c for c in cols if c in results.columns]
            simplified_df = results[available_cols].copy()
            # Format entry_time for compact CSV
            if 'entry_time' in simplified_df.columns:
                simplified_df['entry_time'] = pd.to_datetime(simplified_df['entry_time'], utc=True).dt.strftime("%Y-%m-%d %H:%M")
            simple_name = f"trades_simple{tag}.csv" if tag else "trades_simple.csv"
            simple_path = os.path.join(final_out_dir, simple_name)
            simplified_df.to_csv(simple_path, index=False)
            print(f"Saved simple results to: {simple_path}")
        except Exception as e:
            print(f"⚠️ Failed to write simple results: {e}")

    else:
        print("No trades were executed.")

    if args.plot:
        df_plot = pd.read_csv(args.input_csv)
        df_idx = df_plot.copy()
        df_idx["timestamp"] = pd.to_datetime(df_idx["timestamp"], utc=True)
        df_idx = df_idx.set_index("timestamp")
        dir_plot, st_plot = compute_supertrend(df_idx, cfg.st_length, cfg.st_multiplier)
        df_plot["supertrend"] = st_plot.values
        df_plot["direction"] = dir_plot.values
        if args.plot_latest_only:
            latest_path = os.path.join(final_out_dir, "latest.html")
            plot_supertrend(
                df_plot,
                results,
                latest_path,
                title=f"{base} — ST {cfg.st_length} x {cfg.st_multiplier}{(' — ' + args.run_tag) if args.run_tag else ''}",
                cap_pips=None if args.plot_lite else cfg.max_sl_distance_pips,
                entry_hours=entry_hours,
                pip_size=cfg.pip_size,
                lite=args.plot_lite,
            )
            print(f"Saved latest (only) plot to: {latest_path}")
        else:
            plot_name = f"plot{tag}.html" if tag else "plot.html"
            out_html = args.plot_html or os.path.join(final_out_dir, plot_name)
            plot_supertrend(
                df_plot,
                results,
                out_html,
                title=f"{base} — ST {cfg.st_length} x {cfg.st_multiplier}{(' — ' + args.run_tag) if args.run_tag else ''}",
                cap_pips=None if args.plot_lite else cfg.max_sl_distance_pips,
                entry_hours=entry_hours,
                pip_size=cfg.pip_size,
                lite=args.plot_lite,
            )
            print(f"Saved plot to: {out_html}")
            latest_path = os.path.join(final_out_dir, "latest.html")
            try:
                with open(out_html, "r", encoding="utf-8") as src, open(latest_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
                print(f"Saved latest plot to: {latest_path}")
            except Exception as e:
                print(f"⚠️ Failed to write latest.html: {e}")

    


if __name__ == "__main__":
    sys.exit(main())
