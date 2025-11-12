"""Quick check of data range."""
import pandas as pd

df = pd.read_csv("data/combined_xauusd_1min_full.csv")
print(f"Columns: {list(df.columns)}")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Total rows: {len(df):,}")
df['date'] = pd.to_datetime(df['timestamp']).dt.date
print(f"Days: {df['date'].nunique()}")
print(f"\nFirst row: {df.iloc[0].to_dict()}")
print(f"Last row: {df.iloc[-1].to_dict()}")
