import os
import glob
import re
import pandas as pd
import numpy as np


def compute_metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_pips": 0.0,
            "avg_trade": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "best_trade": np.nan,
            "worst_trade": np.nan,
            "profit_factor": np.nan,
            "max_drawdown": 0.0,
            "start": None,
            "end": None,
        }

    # Ensure pips column numeric
    df = df.copy()
    df["pips"] = pd.to_numeric(df.get("pips"), errors="coerce").fillna(0.0)

    total = len(df)
    wins = (df["pips"] > 0).sum()
    losses = (df["pips"] < 0).sum()
    win_rate = (wins / total) if total else 0.0
    avg_trade = df["pips"].mean() if total else 0.0
    avg_win = df.loc[df["pips"] > 0, "pips"].mean() if wins > 0 else 0.0
    avg_loss = df.loc[df["pips"] < 0, "pips"].mean() if losses > 0 else 0.0
    best_trade = df["pips"].max() if total else np.nan
    worst_trade = df["pips"].min() if total else np.nan
    gross_gain = df.loc[df["pips"] > 0, "pips"].sum()
    gross_loss = df.loc[df["pips"] < 0, "pips"].sum()
    profit_factor = (gross_gain / abs(gross_loss)) if gross_loss != 0 else (np.inf if gross_gain > 0 else np.nan)

    # Equity curve and max drawdown
    equity = df["pips"].cumsum()
    running_max = equity.cummax()
    drawdowns = equity - running_max
    max_drawdown = drawdowns.min() if not drawdowns.empty else 0.0

    # Time range
    start = pd.to_datetime(df.get("entry_time"), utc=True, errors="coerce").min()
    end = pd.to_datetime(df.get("entry_time"), utc=True, errors="coerce").max()

    return {
        "total_trades": int(total),
        "wins": int(wins),
        "losses": int(losses),
        "win_rate": float(win_rate),
        "total_pips": float(df["pips"].sum()),
        "avg_trade": float(avg_trade),
        "avg_win": float(avg_win) if not np.isnan(avg_win) else 0.0,
        "avg_loss": float(avg_loss) if not np.isnan(avg_loss) else 0.0,
        "best_trade": float(best_trade) if pd.notna(best_trade) else np.nan,
        "worst_trade": float(worst_trade) if pd.notna(worst_trade) else np.nan,
        "profit_factor": float(profit_factor) if np.isfinite(profit_factor) else np.nan,
        "max_drawdown": float(max_drawdown) if pd.notna(max_drawdown) else 0.0,
        "start": start.isoformat() if pd.notna(start) else None,
        "end": end.isoformat() if pd.notna(end) else None,
    }


def find_trades_csv(folder: str) -> str | None:
    # Prefer exact 'trades.csv', else first matching 'trades_*.csv'
    exact = os.path.join(folder, "trades.csv")
    if os.path.exists(exact):
        return exact
    matches = glob.glob(os.path.join(folder, "trades_*.csv"))
    return matches[0] if matches else None


def parse_combo_timeframes(label: str) -> list[str]:
    """Parse timeframe tokens from a combo folder label like:
    - combo_1m_5m_15m
    - combo_1m_15m_k2of2
    Returns a list of timeframe strings (e.g., ["1m","5m","15m"]).
    Returns [] if not a combo label.
    """
    if not label.startswith("combo_"):
        return []
    rest = label[len("combo_") :]
    tokens = rest.split("_") if rest else []
    # Drop a trailing kXofN token if present
    if tokens and re.fullmatch(r"k\d+of\d+", tokens[-1]):
        tokens = tokens[:-1]
    # Filter obvious timeframe tokens (defensive)
    tfs = [t for t in tokens if re.fullmatch(r"(\d+m|\dh)", t)]
    # If nothing matched the strict pattern, fall back to all tokens (older labels)
    return tfs if tfs else tokens


def load_up_days_for_tf(tf_label: str) -> set:
    """Load the set of dates (datetime.date) where the given timeframe is Up.
    Expects files like data/trend/ema200_trend_by_date_<tf>.csv with columns ['date','trend'].
    Returns empty set on any issue.
    """
    tf_label = tf_label.strip().lower()
    tf_file = os.path.join("data", "trend", f"ema200_trend_by_date_{tf_label}.csv")
    if not os.path.exists(tf_file):
        return set()
    try:
        fdf = pd.read_csv(tf_file)
        date_col = "date" if "date" in fdf.columns else ("Date" if "Date" in fdf.columns else None)
        if not date_col or "trend" not in fdf.columns:
            return set()
        ts = pd.to_datetime(fdf[date_col], utc=True, errors="coerce").dt.date
        tvals = fdf["trend"].astype(str).str.strip().str.lower()
        ups = ts[(tvals == "up") & ts.notna()]
        return set(ups.unique().tolist())
    except Exception:
        return set()


def main():
    base_dir = os.path.join("results", "trends")

    # Discover all subdirectories (timeframes and combinations like combo_1m_5m_15m)
    subdirs = []
    if os.path.isdir(base_dir):
        for name in os.listdir(base_dir):
            path = os.path.join(base_dir, name)
            if os.path.isdir(path):
                subdirs.append(name)

    rows = []
    upcount_rows = []
    for label in sorted(subdirs):
        tf_dir = os.path.join(base_dir, label)
        trades_path = find_trades_csv(tf_dir)
        if not trades_path or not os.path.exists(trades_path):
            continue
        try:
            df = pd.read_csv(trades_path)
        except Exception:
            continue
        m = compute_metrics(df)
        m["timeframe"] = label
        m["file"] = os.path.relpath(trades_path).replace("\\", "/")
        rows.append(m)

        # Up-count bucket metrics for combo folders
        combo_tfs = parse_combo_timeframes(label)
        if combo_tfs:
            # Build per-TF Up-day sets
            tf_up_sets = {tf: load_up_days_for_tf(tf) for tf in combo_tfs}
            # Skip if no TF up-sets could be loaded
            if any(len(s) > 0 for s in tf_up_sets.values()):
                tmp = df.copy()
                # Parse entry_time to date
                et = pd.to_datetime(tmp.get("entry_time"), utc=True, errors="coerce")
                entry_dates = et.dt.date
                # Compute up-count per trade (missing/invalid dates count as 0)
                counts = []
                for d in entry_dates:
                    if pd.isna(d):
                        counts.append(0)
                        continue
                    c = 0
                    for tf, up_set in tf_up_sets.items():
                        if d in up_set:
                            c += 1
                    counts.append(c)
                tmp["up_count"] = counts

                # Group by up_count and compute metrics per bucket
                for upc, g in tmp.groupby("up_count"):
                    gm = compute_metrics(g)
                    gm["timeframe"] = label
                    gm["up_count"] = int(upc)
                    gm["file"] = os.path.relpath(trades_path).replace("\\", "/")
                    upcount_rows.append(gm)

    if not rows:
        print("No timeframe results found to aggregate.")
        return 0

    out_dir = base_dir
    os.makedirs(out_dir, exist_ok=True)
    summary_df = pd.DataFrame(rows)[[
        "timeframe", "total_trades", "wins", "losses", "win_rate", "total_pips",
        "avg_trade", "avg_win", "avg_loss", "best_trade", "worst_trade",
        "profit_factor", "max_drawdown", "start", "end", "file"
    ]]
    csv_path = os.path.join(out_dir, "aggregate_summary.csv")
    summary_df.sort_values(by=["timeframe"], inplace=True)
    summary_df.to_csv(csv_path, index=False)
    print(f"Saved aggregate summary CSV to: {csv_path}")

    # Also write a quick Markdown table
    md_path = os.path.join(out_dir, "aggregate_summary.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# SuperTrend Aggregate Summary\n\n")
        f.write("| Timeframe | Trades | Win% | Total Pips | PF | Max DD | Start | End |\n")
        f.write("|---:|---:|---:|---:|---:|---:|:---|:---|\n")
        for r in summary_df.itertuples(index=False):
            f.write(
                f"| {r.timeframe} | {r.total_trades} | {r.win_rate*100:.2f}% | {r.total_pips:.1f} | "
                f"{(r.profit_factor if pd.notna(r.profit_factor) else 'n/a')} | {r.max_drawdown:.1f} | "
                f"{r.start if r.start else ''} | {r.end if r.end else ''} |\n"
            )
    print(f"Saved aggregate summary Markdown to: {md_path}")

    # If we computed any up-count bucket rows, write separate summaries
    if upcount_rows:
        up_df = pd.DataFrame(upcount_rows)[[
            "timeframe", "up_count", "total_trades", "wins", "losses", "win_rate", "total_pips",
            "avg_trade", "avg_win", "avg_loss", "best_trade", "worst_trade",
            "profit_factor", "max_drawdown", "start", "end", "file"
        ]]
        up_df.sort_values(by=["timeframe", "up_count"], inplace=True)
        up_csv = os.path.join(out_dir, "aggregate_upcount_summary.csv")
        up_df.to_csv(up_csv, index=False)
        print(f"Saved up-count aggregate CSV to: {up_csv}")

        up_md = os.path.join(out_dir, "aggregate_upcount_summary.md")
        with open(up_md, "w", encoding="utf-8") as f:
            f.write("# Up-count Bucket Summary\n\n")
            f.write("Higher up_count means more timeframes agreed on 'Up' that day.\n\n")
            f.write("| Timeframe | Up-count | Trades | Win% | Total Pips | PF | Max DD | Start | End |\n")
            f.write("|:--|--:|--:|--:|--:|--:|--:|:--|:--|\n")
            for r in up_df.itertuples(index=False):
                f.write(
                    f"| {r.timeframe} | {r.up_count} | {r.total_trades} | {r.win_rate*100:.2f}% | {r.total_pips:.1f} | "
                    f"{(r.profit_factor if pd.notna(r.profit_factor) else 'n/a')} | {r.max_drawdown:.1f} | "
                    f"{r.start if r.start else ''} | {r.end if r.end else ''} |\n"
                )
        print(f"Saved up-count aggregate Markdown to: {up_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
