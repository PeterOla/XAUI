import pandas as pd
import numpy as np

print("="*70)
print("CHECKING FOR LOOK-AHEAD BIAS IN NEWS DATA")
print("="*70)

# Load headlines
print("\nLoading headlines...")
headlines = pd.read_csv('sentiments/news/headlines_gold_specific.csv')
headlines['timestamp'] = pd.to_datetime(headlines['timestamp'])
headlines['entry_time'] = pd.to_datetime(headlines['entry_time'])

print(f"Total headlines: {len(headlines):,}")
print(f"Unique trades: {headlines['event_index'].nunique()}")

# Calculate time difference: headline timestamp - entry time
headlines['time_diff_minutes'] = (headlines['timestamp'] - headlines['entry_time']).dt.total_seconds() / 60

print(f"\n{'='*70}")
print("TIME DIFFERENCE ANALYSIS (Headline Time - Entry Time)")
print("="*70)
print(f"Negative = headline BEFORE entry (GOOD ✅)")
print(f"Positive = headline AFTER entry (BAD ❌ - LOOK AHEAD BIAS)")
print()

# Statistics
print(f"Min time diff: {headlines['time_diff_minutes'].min():.1f} minutes")
print(f"Max time diff: {headlines['time_diff_minutes'].max():.1f} minutes")
print(f"Mean time diff: {headlines['time_diff_minutes'].mean():.1f} minutes")
print(f"Median time diff: {headlines['time_diff_minutes'].median():.1f} minutes")

# Count future headlines (look-ahead bias)
future_headlines = headlines[headlines['time_diff_minutes'] > 0]
past_headlines = headlines[headlines['time_diff_minutes'] <= 0]

print(f"\n{'='*70}")
print("LOOK-AHEAD BIAS CHECK")
print("="*70)
print(f"Headlines BEFORE entry (valid): {len(past_headlines):,} ({len(past_headlines)/len(headlines)*100:.2f}%)")
print(f"Headlines AFTER entry (BIAS!):  {len(future_headlines):,} ({len(future_headlines)/len(headlines)*100:.2f}%)")

if len(future_headlines) > 0:
    print(f"\n⚠️  WARNING: LOOK-AHEAD BIAS DETECTED!")
    print(f"   {len(future_headlines):,} headlines are timestamped AFTER the entry time")
    print(f"\n   Sample future headlines:")
    sample = future_headlines.nsmallest(5, 'time_diff_minutes')[['entry_time', 'timestamp', 'time_diff_minutes', 'title']]
    for idx, row in sample.iterrows():
        print(f"   - Entry: {row['entry_time']}, Headline: {row['timestamp']} (+{row['time_diff_minutes']:.0f}m)")
        print(f"     '{row['title'][:80]}...'")
        print()
else:
    print(f"\n✅ NO LOOK-AHEAD BIAS: All headlines are timestamped BEFORE their entry time")

# Check distribution by time bucket
print(f"\n{'='*70}")
print("TIME DIFFERENCE DISTRIBUTION")
print("="*70)
bins = [-np.inf, -180, -120, -60, -30, -10, 0, 10, 30, 60, 120, 180, np.inf]
labels = ['<-3h', '-3h to -2h', '-2h to -1h', '-1h to -30m', '-30m to -10m', 
          '-10m to 0', '0 to +10m', '+10m to +30m', '+30m to +1h', '+1h to +2h', '+2h to +3h', '>+3h']
headlines['time_bucket'] = pd.cut(headlines['time_diff_minutes'], bins=bins, labels=labels)

dist = headlines['time_bucket'].value_counts().sort_index()
for bucket, count in dist.items():
    pct = count / len(headlines) * 100
    marker = "⚠️ " if '+' in str(bucket) else "✅"
    print(f"{marker} {bucket:>15}: {count:>6,} ({pct:>5.2f}%)")

print(f"\n{'='*70}")
print("CONCLUSION")
print("="*70)

if len(future_headlines) == 0:
    print("✅ DATA IS CLEAN - No look-ahead bias detected")
    print("   All headlines are from BEFORE the trade entry time")
elif len(future_headlines) / len(headlines) < 0.01:
    print("⚠️  MINIMAL BIAS - <1% of headlines are future (likely API timing)")
    print("   Consider filtering these out but impact is negligible")
else:
    print("❌ SIGNIFICANT BIAS - Need to fix data collection window")
    print(f"   {len(future_headlines)/len(headlines)*100:.1f}% of headlines are from the FUTURE")
    print("   This would invalidate the backtest results!")
