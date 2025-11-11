"""Quick diagnostic: check predicted probability distribution."""
import pickle
import pandas as pd
import numpy as np

# Load model
model = pickle.load(open("ml/models/trade_quality_lr.pkl", "rb"))

# Load test data
df = pd.read_parquet("data/features/trades_features.parquet")
test_idx = pd.to_datetime(pd.read_csv("data/features/splits/test_indices.csv")["entry_bar"])
test = df.loc[test_idx]

# Predict
X = test[model.feature_names_in_].fillna(test[model.feature_names_in_].median()).fillna(0)
y = test["label_win"].astype(int)
proba = model.predict_proba(X)[:, 1]

# Stats
print(f"Test set: {len(test)} trades, {y.sum()} wins ({y.mean()*100:.1f}%)")
print(f"\nPredicted probabilities:")
print(f"  Min:  {proba.min():.4f}")
print(f"  Max:  {proba.max():.4f}")
print(f"  Mean: {proba.mean():.4f}")
print(f"  Std:  {proba.std():.4f}")
print(f"\nThreshold coverage:")
print(f"  % above 0.50: {(proba >= 0.5).mean() * 100:.1f}%")
print(f"  % above 0.40: {(proba >= 0.4).mean() * 100:.1f}%")
print(f"  % above 0.30: {(proba >= 0.3).mean() * 100:.1f}%")
print(f"\nDeciles:")
for q in [0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]:
    print(f"  {q*100:.0f}th: {np.quantile(proba, q):.4f}")

# Check class balance
print(f"\nBaseline PF: {test['pips'][test['pips'] > 0].sum() / abs(test['pips'][test['pips'] < 0].sum()):.2f}")
