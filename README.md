# XAUUSD SuperTrend Strategy

This repository contains a clean SuperTrend backtest implementation for XAUUSD (Gold) trading using 1-minute price data.

## Data Requirements

**Important Note**: The data files have been removed from this repository due to their large size. If you need access to the historical data files, please reach out to: **Olalerupeter@gmail.com**

The strategy expects 1-minute OHLC data in CSV format with the following structure:
- `timestamp,Open,High,Low,Close` (UTC timezone; Volume optional)
- Files should be placed in the `data/` directory

## Quick Start

```powershell
# Run the strategy with default settings
python scripts/base_strategy.py --input-csv data/your_data_file.csv --entry-hours 13-16 --plot
```

This will:
- Run the SuperTrend strategy on your data
- Output results to `results/trends/` directory (full trade CSV, simplified CSV, and interactive HTML plot)
- Apply entry hours filter (13-16 UTC) and trend filter by default

## EMA200 Daily Trend Filter

The strategy includes an optional EMA200-based daily trend filter:

-- **Trend file format**: `data/trend/ema200_trend_by_date_1m.csv` (default alias) with columns `date,trend` where trend ∈ {Up, Down}
- **How it's computed**:
  - Resample 1‑minute Close to 15‑minute intervals
  - Compute EMA200 on the 15‑minute Close prices
  - Shift index +1h (UTC → UTC+1), then sample at 12:45
  - Trend = Up if Close > EMA200, else Down

- **Generate trend file**:
```powershell
# Generate six timeframes and write a 1m compatibility alias under data/trend/
python scripts/generate_ema200_trend.py --input-csv data/your_data_file.csv --resamples 1m,5m,15m,30m,1h,4h --out-csv data/trend/ema200_trend_by_date_1m.csv
```
Generated files:
- `data/trend/ema200_trend_by_date_5m.csv`
- `data/trend/ema200_trend_by_date_15m.csv`
- `data/trend/ema200_trend_by_date_30m.csv`
- `data/trend/ema200_trend_by_date_1h.csv`
- `data/trend/ema200_trend_by_date_4h.csv`
- `data/trend/ema200_trend_by_date_1m.csv` (also written as the compatibility alias when provided via --out-csv)

- **Usage in strategy**:
  - Auto-loaded by default; disable with `--no-trend-filter`
  - Choose trend direction with `--trend up|down|both` (default: `up`)

## Strategy Configuration

### Command Line Options

```powershell
python scripts/base_strategy.py --help
```

Key parameters:
- `--input-csv`: Path to your 1-minute OHLC CSV file
- `--entry-hours`: UTC hour window for entries (e.g., "13-16" or "all")
- `--st-length`: SuperTrend length parameter (default: 10)
- `--st-multiplier`: SuperTrend multiplier (default: 3.6)
- `--max-sl-distance-pips`: Maximum stop loss distance in pips (default: 520)
- `--trend`: Trend filter direction - "up", "down", or "both" (default: "up")
- `--long-only` / `--short-only`: Restrict to only long or short trades
- `--plot`: Generate interactive HTML plot
- `--out-dir`: Output directory for results

### Strategy Rules

1. **Entry Pattern**: SuperTrend flip → alternating candle → entry on following candle
2. **Entry Hours**: Only during specified UTC hours (default: 13-16)
3. **Stop Loss**: Trails with SuperTrend line, capped at max distance
4. **Exit**: When price crosses SuperTrend line (Low ≤ ST for longs, High ≥ ST for shorts)
5. **Trend Filter**: Optional daily EMA200 filter (default: only trade on "Up" trend days)

## Output Files

The strategy generates output per timeframe under `results/trends/<timeframe>/` (default timeframe: 1m):

For example, for `--timeframe 1m`:
- `results/trends/1m/trades.csv`
- `results/trends/1m/trades_simple.csv`
- `results/trends/1m/plot.html`
- `results/trends/1m/latest.html`

Notes:
- You can tag filenames using `--run-tag mytag` which appends suffixes like `trades_mytag.csv`.
- Override the base output directory with `--out-dir` (the timeframe subfolder is appended automatically).

## Technical Notes

- **Pip Size**: 0.01 USD per pip (XAUUSD standard)
- **SuperTrend**: Uses Pine Script-style RMA (Rolling Moving Average) for ATR calculation
- **Exit Logic**: Prefers previous bar's SuperTrend value to avoid post-flip exit jumps
- **Timezone**: All data and times are in UTC

## Repository Structure

```
├── scripts/
│   ├── base_strategy.py          # Main strategy implementation
│   └── generate_ema200_trend.py  # EMA200 trend file generator
├── data/                         # Place your CSV files here (gitignored). Trend outputs are under data/trend/
├── results/trends/               # Strategy outputs grouped by timeframe (e.g., 1m/, 5m/)
└── README.md                     # This file
```

## Installation & Dependencies

Ensure you have the required Python packages installed:

```powershell
pip install -r requirements.txt
```

Or manually install the dependencies:

```powershell
pip install pandas numpy plotly
```

## Contact

For access to historical data files or questions about the strategy, please contact: **Olalerupeter@gmail.com**