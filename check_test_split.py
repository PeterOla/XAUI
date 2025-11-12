import pandas as pd

# Load sentiment features
df = pd.read_parquet('data/features/trades_sentiment_gold_refined.parquet')
df['entry_time'] = pd.to_datetime(df['entry_time'])

# Calculate test set split (last 15%)
n = len(df)
test_start = int(n * 0.85)
test_df = df.iloc[test_start:]

print(f'Total trades: {n}')
print(f'Test set start index: {test_start}')
print(f'Test set size: {len(test_df)}')
print(f'Test date range: {test_df["entry_time"].min()} to {test_df["entry_time"].max()}')

# Filter for moderate_bearish
moderate_bearish = test_df[(test_df['headline_count'] >= 5) & (test_df['net_sentiment'] < -0.1)]
print(f'\nModerate bearish filter on test set: {len(moderate_bearish)} trades')
print(f'Expected: 37 trades')
