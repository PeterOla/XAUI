import pandas as pd

m = pd.read_parquet("data/features/trades_features_2490_v3_with_news_v2.parquet")
print(f"has_event_nearby sum: {m['has_event_nearby'].sum()}")
print(f"has_event_nearby dtype: {m['has_event_nearby'].dtype}")
print(f"\nColumns: {list(m.columns)}")
