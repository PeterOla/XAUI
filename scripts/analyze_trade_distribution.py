"""Analyze trade distribution across years."""
import pandas as pd

df = pd.read_csv("results/baseline_2015_2025_up_buy_full/15m/trades_simple_up_buy_only.csv")
df['entry_time'] = pd.to_datetime(df['entry_time'])
df['year'] = df['entry_time'].dt.year

print("Trade distribution by year:")
year_stats = df.groupby('year').agg({
    'pips': ['count', 'sum', 'mean'],
}).round(1)
year_stats.columns = ['trades', 'total_pips', 'avg_pips']
print(year_stats)

print(f"\nDate range: {df['entry_time'].min()} to {df['entry_time'].max()}")
print(f"Total trades: {len(df)}")
print(f"Years covered: {df['year'].nunique()}")
