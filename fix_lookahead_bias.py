import pandas as pd

print("Fixing look-ahead bias in headlines...")
print("="*70)

# Load headlines
headlines = pd.read_csv('sentiments/news/headlines_gold_specific.csv')
headlines['timestamp'] = pd.to_datetime(headlines['timestamp'])
headlines['entry_time'] = pd.to_datetime(headlines['entry_time'])

print(f"Original headlines: {len(headlines):,}")

# Remove headlines that are AFTER entry time
# Keep only headlines where timestamp < entry_time (strictly before)
headlines_clean = headlines[headlines['timestamp'] < headlines['entry_time']].copy()

print(f"Headlines removed: {len(headlines) - len(headlines_clean):,}")
print(f"Clean headlines: {len(headlines_clean):,}")
print(f"Percentage kept: {len(headlines_clean)/len(headlines)*100:.2f}%")

# Verify no future headlines remain
future_check = headlines_clean[headlines_clean['timestamp'] >= headlines_clean['entry_time']]
assert len(future_check) == 0, "Still have future headlines!"

print(f"\n✅ Verification: No future headlines remain")

# Save clean version
out_path = 'sentiments/news/headlines_gold_specific_clean.csv'
headlines_clean.to_csv(out_path, index=False)
print(f"\n💾 Saved clean headlines to: {out_path}")

# Statistics
print(f"\n{'='*70}")
print("CLEAN DATA STATISTICS")
print("="*70)

headlines_clean['time_diff_minutes'] = (headlines_clean['timestamp'] - headlines_clean['entry_time']).dt.total_seconds() / 60

print(f"Time range (headline - entry):")
print(f"  Min: {headlines_clean['time_diff_minutes'].min():.1f} minutes (most historical)")
print(f"  Max: {headlines_clean['time_diff_minutes'].max():.1f} minutes (most recent before entry)")
print(f"  Mean: {headlines_clean['time_diff_minutes'].mean():.1f} minutes")
print(f"  Median: {headlines_clean['time_diff_minutes'].median():.1f} minutes")

print(f"\nUnique trades with headlines: {headlines_clean['event_index'].nunique()}")
print(f"Avg headlines per trade: {len(headlines_clean) / headlines_clean['event_index'].nunique():.1f}")

print(f"\n✅ Data is now clean and ready for sentiment analysis")
