import argparse
import itertools
import os
import subprocess
import sys
from typing import List


def parse_args(argv: List[str]):
    p = argparse.ArgumentParser(description="Run base_strategy over combinations of EMA200 trend timeframes")
    p.add_argument("--tfs", default="1m,5m,15m,30m,1h,4h", help="Comma-separated list of timeframes to combine")
    p.add_argument("--min-size", type=int, default=2, help="Minimum combination size (default: 2)")
    p.add_argument("--max-size", type=int, default=None, help="Maximum combination size; default: all")
    p.add_argument("--trend", choices=["up","down","both"], default="up", help="Trend side to require in all TFs")
    p.add_argument("--input-csv", default=None, help="Pass through to base_strategy --input-csv")
    p.add_argument("--date-start", default=None)
    p.add_argument("--date-end", default=None)
    p.add_argument("--no-plot", action="store_true")
    p.add_argument("--plot", action="store_true")
    p.add_argument("--plot-lite", action="store_true")
    p.add_argument("--plot-latest-only", action="store_true")
    p.add_argument("--limit-rows", type=int, default=None)
    p.add_argument("--extra", default="", help="Additional args to append raw to base_strategy")
    return p.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    tfs = [s.strip() for s in args.tfs.split(',') if s.strip()]
    if not tfs:
        print("No timeframes provided")
        return 1
    min_k = max(1, args.min_size)
    max_k = args.max_size or len(tfs)
    ran = 0

    base_py = os.path.join("scripts", "base_strategy.py")
    if not os.path.exists(base_py):
        print(f"base_strategy not found at {base_py}")
        return 2

    for k in range(min_k, max_k + 1):
        for combo in itertools.combinations(tfs, k):
            combo_str = ",".join(combo)
            cmd = [sys.executable, base_py, "--trend-tfs", combo_str, "--trend", args.trend]
            if args.input_csv:
                cmd += ["--input-csv", args.input_csv]
            if args.date_start:
                cmd += ["--date-start", args.date_start]
            if args.date_end:
                cmd += ["--date-end", args.date_end]
            if args.limit_rows:
                cmd += ["--max-rows", str(args.limit_rows)]
            if args.no_plot:
                # Prefer no plot
                pass
            elif args.plot:
                cmd += ["--plot"]
                if args.plot_lite:
                    cmd += ["--plot-lite"]
                if args.plot_latest_only:
                    cmd += ["--plot-latest-only"]
            if args.extra:
                # naive split; assume user provides properly formatted
                cmd += args.extra.split()

            print(f"\n▶ Running combo: {combo_str}")
            try:
                subprocess.run(cmd, check=True)
                ran += 1
            except subprocess.CalledProcessError as e:
                print(f"⚠️ Combo failed {combo_str}: {e}")
                continue

    print(f"Done. Ran {ran} combinations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
