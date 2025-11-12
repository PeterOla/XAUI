#!/usr/bin/env python3
"""
Fetch headlines from GDELT for event windows.

- Input: events_offline.csv with window_start, window_end (UTC), entry_time, etc.
- Output: headlines_raw.csv with columns [timestamp, title, url, sourcecountry, lang, event_index]

Notes:
- Uses GDELT Doc API (no API key). Results are best-effort and may not be exhaustive.
- Use --max-events to limit requests for quick validation.
"""

import argparse
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import requests
import pandas as pd

BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
HEADERS = {
    "User-Agent": "XAUi-Research/1.0 (+https://example.com)",
    "Accept": "application/json, text/plain;q=0.9, */*;q=0.8",
}


def fmt_gdelt_time(ts: pd.Timestamp) -> str:
    if pd.isna(ts):
        return ""
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    ts = ts.tz_convert("UTC")
    return ts.strftime("%Y%m%d%H%M%S")


@dataclass
class Config:
    events_csv: Path
    out_csv: Path
    query: str = '"gold price" OR "gold rally" OR "gold falls" OR xauusd OR "spot gold"'
    max_records: int = 250
    throttle_sec: float = 0.3
    max_events: Optional[int] = None
    lang: Optional[str] = "English"


def parse_args() -> Config:
    ap = argparse.ArgumentParser(description="Fetch headlines from GDELT for event windows")
    ap.add_argument("--events-csv", required=False, default=str(Path("sentiments/news") / "events_offline.csv"))
    ap.add_argument("--out-csv", required=False, default=str(Path("sentiments/news") / "headlines_raw.csv"))
    ap.add_argument("--query", default='"gold price" OR "gold rally" OR "gold falls" OR xauusd OR "spot gold"')
    ap.add_argument("--max-records", type=int, default=250)
    ap.add_argument("--throttle-sec", type=float, default=0.3)
    ap.add_argument("--max-events", type=int, default=50, help="Limit number of events to fetch for (None for all)")
    ap.add_argument("--lang", type=str, default="English", help="Restrict to this GDELT source language (e.g., English). Empty for no filter.")
    args = ap.parse_args()
    return Config(
        events_csv=Path(args.events_csv),
        out_csv=Path(args.out_csv),
        query=args.query,
        max_records=args.max_records,
        throttle_sec=args.throttle_sec,
        max_events=(None if args.max_events in (None, -1) else int(args.max_events)),
        lang=(args.lang if args.lang and args.lang.strip() else None),
    )


def fetch_for_window(q: str, start: pd.Timestamp, end: pd.Timestamp, max_records: int, lang: Optional[str]) -> List[dict]:
    # GDELT Doc API only has data from 2017 onwards
    GDELT_START_DATE = pd.Timestamp("2017-01-01", tz="UTC")
    if end < GDELT_START_DATE:
        # Skip requests for dates before GDELT coverage
        return []
    
    # GDELT requires OR queries to be wrapped in parentheses
    q_wrapped = q
    if " OR " in q and "(" not in q:
        q_wrapped = f"({q})"
    # Append language filter
    if lang:
        q_wrapped = f"{q_wrapped} AND sourcelang:{lang.lower()}"
    params = {
        "query": q_wrapped,
        "mode": "ArtList",
        "maxrecords": str(max_records),
        "sort": "datedesc",
        "format": "json",
        "startdatetime": fmt_gdelt_time(start),
        "enddatetime": fmt_gdelt_time(end),
    }
    last_err = None
    for attempt in range(3):
        try:
            r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
            
            # Handle rate limiting gracefully
            if r.status_code == 429:
                wait_time = 2.0 * (attempt + 1)  # Exponential backoff
                print(f"⚠️  Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            r.raise_for_status()
            ctype = r.headers.get("Content-Type", "")
            if "json" not in ctype.lower():
                # Some responses are HTML error pages
                if "Invalid query start date" in r.text:
                    # Date outside GDELT coverage, return empty
                    return []
                last_err = f"Non-JSON response ({ctype}): {r.text[:200]}"
                time.sleep(0.6 * (attempt + 1))
                continue
            data = r.json()
            arts = data.get("articles", [])
            out = []
            for a in arts:
                out.append({
                    "timestamp": a.get("seendate"),
                    "title": a.get("title"),
                    "url": a.get("url"),
                    "sourcecountry": a.get("sourcecountry"),
                    "lang": a.get("language"),
                })
            return out
        except Exception as e:
            last_err = str(e)
            time.sleep(0.6 * (attempt + 1))
    raise RuntimeError(last_err or "Unknown fetch error")


def run(cfg: Config) -> None:
    ev = pd.read_csv(cfg.events_csv)
    if not {"window_start", "window_end"}.issubset(set(ev.columns)):
        raise SystemExit("events_offline.csv missing window_start/window_end")
    ev["window_start"] = pd.to_datetime(ev["window_start"], utc=True, errors="coerce")
    ev["window_end"] = pd.to_datetime(ev["window_end"], utc=True, errors="coerce")

    # Filter to GDELT date range (2017+)
    GDELT_START_DATE = pd.Timestamp("2017-01-01", tz="UTC")
    ev_filtered = ev[ev["window_end"] >= GDELT_START_DATE].copy()
    skipped_count = len(ev) - len(ev_filtered)
    
    if skipped_count > 0:
        print(f"⚠️  Skipping {skipped_count} events before GDELT coverage (2017-01-01)")
    print(f"📊 Fetching headlines for {len(ev_filtered)} events from {ev_filtered['window_end'].min()} to {ev_filtered['window_end'].max()}")

    rows = []
    err_rows = []
    iter_rows = list(ev_filtered.itertuples())
    if cfg.max_events is not None:
        iter_rows = iter_rows[: cfg.max_events]

    for idx, r in enumerate(iter_rows):
        start = getattr(r, "window_start")
        end = getattr(r, "window_end")
        event_idx = getattr(r, "Index")  # Original index from CSV
        
        if (idx + 1) % 100 == 0:
            print(f"Progress: {idx + 1}/{len(iter_rows)} events processed...")
        
        try:
            arts = fetch_for_window(cfg.query, start, end, cfg.max_records, cfg.lang)
            if arts:  # Only add if we got results
                for a in arts:
                    rows.append({
                        **a,
                        "event_index": event_idx,
                        "entry_time": getattr(r, "entry_time"),
                    })
        except Exception as e:
            # Continue on errors, record a note row and also keep a small log
            msg = f"ERROR: {e}"
            err_rows.append({
                "event_index": event_idx,
                "entry_time": getattr(r, "entry_time"),
                "window_start": start,
                "window_end": end,
                "error": msg,
            })
        time.sleep(cfg.throttle_sec)

    out_df = pd.DataFrame(rows)
    # Normalize timestamp to UTC
    if not out_df.empty:
        out_df["timestamp"] = pd.to_datetime(out_df["timestamp"], errors="coerce", utc=True)
        # Post-filter by language if requested (defense-in-depth)
        if cfg.lang and "lang" in out_df.columns:
            out_df = out_df[out_df["lang"].astype(str).str.lower() == cfg.lang.lower()]
    cfg.out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(cfg.out_csv, index=False)
    # Optional error log
    if err_rows:
        err_path = cfg.out_csv.parent / "headlines_errors.csv"
        pd.DataFrame(err_rows).to_csv(err_path, index=False)
        print(f"Encountered {len(err_rows)} errors → {err_path}")
    print(f"Wrote {len(out_df):,} headlines → {cfg.out_csv}")


if __name__ == "__main__":
    run(parse_args())
