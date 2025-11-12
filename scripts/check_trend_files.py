"""Check trend file counts."""
import pandas as pd

# Check ema200_trend_by_date.csv
df = pd.read_csv("data/ema200_trend_by_date.csv")
print(f"Total rows: {len(df)}")
print(f"Up days: {(df['trend'] == 'Up').sum()}")
print(f"Down days: {(df['trend'] == 'Down').sum()}")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")

# Check if there's a trend file in data/trend/
import os
if os.path.exists("data/trend"):
    print("\n\nFound data/trend/ directory. Contents:")
    for f in os.listdir("data/trend"):
        if f.endswith(".csv"):
            print(f"  - {f}")
            trend_df = pd.read_csv(f"data/trend/{f}")
            print(f"    Rows: {len(trend_df)}, Up days: {(trend_df['trend'] == 'Up').sum()}")
