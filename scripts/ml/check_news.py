import pandas as pd

news = pd.read_parquet("data/features/trades_news_sentiment_2490_v2.parquet")

print("News features sample:")
print(news[["entry_time", "has_event_nearby", "event_impact", "sentiment_0_30min"]].head(20))

print(f"\nhas_event_nearby sum: {news['has_event_nearby'].sum()}")
print(f"has_event_nearby dtype: {news['has_event_nearby'].dtype}")

# Check some trades with events
trades_with_events = news[news["has_event_nearby"] == 1].head(10)
print(f"\nTrades with events: {len(trades_with_events)}")
print(trades_with_events[["entry_time", "event_impact", "minutes_since_event", "sentiment_0_30min"]])
