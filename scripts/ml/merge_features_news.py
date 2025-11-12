"""
Merge technical features with news sentiment features.
"""
import pandas as pd

# Load features
print("Loading technical features...")
tech = pd.read_parquet("data/features/trades_features_2490_v3_enhanced.parquet")
print(f"Technical features: {tech.shape}")

print("Loading news sentiment features...")
news = pd.read_parquet("data/features/trades_news_sentiment_2490_v2.parquet")
print(f"News features: {news.shape}")

# Prepare merge keys - use the original date/entry_time for matching
print("\nPreparing merge...")
# Convert both to datetime and normalize
tech_for_merge = tech.copy()
news_for_merge = news.copy()

# Normalize both to datetime without timezone
tech_for_merge["merge_key"] = pd.to_datetime(tech_for_merge["date"]).dt.tz_localize(None)
news_for_merge["merge_key"] = pd.to_datetime(news_for_merge["entry_time"]).dt.tz_localize(None)

# Merge on the normalized datetime
merged = tech_for_merge.merge(
    news_for_merge.drop(columns=["side", "pips", "label_win", "entry_time"]),
    on="merge_key",
    how="left"
)

# Drop the temp merge key
merged = merged.drop(columns=["merge_key"])

print(f"After merge: {merged['has_event_nearby'].notna().sum()} non-null has_event_nearby")
print(f"Has event nearby (before fill): {merged['has_event_nearby'].sum()}")

# Fill NaN for trades with no nearby events
merged = merged.fillna({
    "sentiment_0_30min": 0,
    "sentiment_30_60min": 0,
    "sentiment_1_3hr": 0,
    "sentiment_today": 0,
    "event_impact": 0,
    "minutes_since_event": 999,
    "has_event_nearby": 0,
})

print(f"\n✅ Merged dataset: {merged.shape[0]} rows × {merged.shape[1]} columns")
print(f"   Features: {merged.shape[1] - 2} (excluding pips, label_win)")

# Save
out_path = "data/features/trades_features_2490_v3_with_news_v2.parquet"
merged.to_parquet(out_path, index=False)
print(f"   Saved to: {out_path}")

# Summary
feature_cols = [c for c in merged.columns if c not in ["pips", "label_win"]]
tech_base_features = [c for c in tech.columns if c not in ["date", "pips", "label_win"]]
news_base_features = [c for c in news.columns if c not in ["entry_time", "side", "pips", "label_win"]]
print(f"\n📊 Feature breakdown:")
print(f"   Technical: {len(tech_base_features)} features")
print(f"   News sentiment: {len(news_base_features)} features")
print(f"   Total: {len(feature_cols)} features")
print(f"\n   Trades with news events: {int(merged['has_event_nearby'].sum())} / {len(merged)}")
