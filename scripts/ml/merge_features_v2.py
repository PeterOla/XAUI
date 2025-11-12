"""
Merge technical features with news sentiment - proper approach.
1. Load trades CSV (has full timestamps)
2. Merge news features with trades on entry_time
3. Merge technical features with result on date
"""
import pandas as pd

# Load original trades
print("Loading trades...")
trades = pd.read_csv("results/baseline_2015_2025_up_both_full/15m/trades.csv")
trades["entry_time"] = pd.to_datetime(trades["entry_time"])
print(f"Trades: {trades.shape}")

# Load news features
print("\nLoading news sentiment features...")
news = pd.read_parquet("data/features/trades_news_sentiment_2490_v2.parquet")
print(f"News features: {news.shape}")
print(f"Trades with events in news: {news['has_event_nearby'].sum()}")

# Merge trades with news on entry_time
trades_with_news = trades.merge(
    news[["entry_time", "sentiment_0_30min", "sentiment_30_60min", "sentiment_1_3hr",
          "sentiment_today", "event_impact", "minutes_since_event", "has_event_nearby"]],
    on="entry_time",
    how="left"
)

print(f"\nAfter merging trades + news: {trades_with_news['has_event_nearby'].notna().sum()} non-null")
print(f"Trades with events: {trades_with_news['has_event_nearby'].sum()}")

# Fill NaN for trades with no events
trades_with_news = trades_with_news.fillna({
    "sentiment_0_30min": 0,
    "sentiment_30_60min": 0,
    "sentiment_1_3hr": 0,
    "sentiment_today": 0,
    "event_impact": 0,
    "minutes_since_event": 999,
    "has_event_nearby": 0,
})

# Load technical features
print("\nLoading technical features...")
tech = pd.read_parquet("data/features/trades_features_2490_v3_enhanced.parquet")
print(f"Technical features: {tech.shape}")

# Extract date from entry_time for merging
trades_with_news["date"] = trades_with_news["entry_time"].dt.date.astype(str)

# Merge with technical features on date
tech_cols = [c for c in tech.columns if c not in ["pips", "label_win"]]
merged = trades_with_news.merge(
    tech[tech_cols],
    on="date",
    how="left",
    suffixes=("", "_tech")
)

# Drop redundant columns from trades (keep only features + labels)
# Get all columns from merged
all_feature_cols = [c for c in merged.columns if c not in [
    "entry_time", "exit_time", "side", "entry", "exit", "final_stop", "date"
]]
merged = merged[all_feature_cols]

# Create binary win label
merged["label_win"] = (merged["pips"] > 0).astype(int)

print(f"\n✅ Final merged dataset: {merged.shape[0]} rows × {merged.shape[1]} columns")
print(f"   Total features: {merged.shape[1] - 2} (excluding pips, label_win)")
print(f"   Trades with news events: {int(merged['has_event_nearby'].sum())} / {len(merged)}")

# Save
out_path = "data/features/trades_features_2490_v3_with_news_v2.parquet"
merged.to_parquet(out_path, index=False)
print(f"   Saved to: {out_path}")
