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
- Output results to `results/` directory (full trade CSV, simplified CSV, and interactive HTML plot)
- Apply entry hours filter (13-16 UTC) and trend filter by default

## EMA200 Daily Trend Filter

The strategy includes an optional EMA200-based daily trend filter:

- **Trend file format**: `data/ema200_trend_by_date.csv` with columns `date,trend` where trend ∈ {Up, Down}
- **How it's computed**:
  - Resample 1‑minute Close to 15‑minute intervals
  - Compute EMA200 on the 15‑minute Close prices
  - Shift index +1h (UTC → UTC+1), then sample at 12:45
  - Trend = Up if Close > EMA200, else Down

- **Generate trend file**:
```powershell
python scripts/generate_ema200_trend.py --input-csv data/your_data_file.csv
```

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

The strategy generates several output files in the `results/` directory:

1. **Full Results CSV**: Complete trade details with entry/exit times, prices, and performance
2. **Simple Results CSV**: Condensed version with key metrics
3. **Interactive Plot**: HTML file with candlestick chart, SuperTrend line, and trade markers
4. **Performance Summary**: Console output with key statistics

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
├── data/                         # Place your CSV files here (gitignored)
├── results/                      # Strategy output files
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