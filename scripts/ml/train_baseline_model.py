"""
Train baseline Logistic Regression + LightGBM for trade quality prediction (Phase 3A).
Outputs: models, feature importance, metadata JSON.
"""
import argparse
import os
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, precision_score, recall_score, confusion_matrix
import pickle

# LightGBM imported conditionally
try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False

def time_split(df, train_pct=0.70, val_pct=0.15):
    """Time-based split (no shuffle)."""
    n = len(df)
    train_end = int(n * train_pct)
    val_end = train_end + int(n * val_pct)
    return df.iloc[:train_end], df.iloc[train_end:val_end], df.iloc[val_end:]

def save_splits(train, val, test, out_dir="data/features/splits"):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    train.index.to_frame().to_csv(os.path.join(out_dir, "train_indices.csv"), index=False)
    val.index.to_frame().to_csv(os.path.join(out_dir, "val_indices.csv"), index=False)
    test.index.to_frame().to_csv(os.path.join(out_dir, "test_indices.csv"), index=False)

def compute_metrics(y_true, y_pred_proba, threshold=0.5):
    y_pred = (y_pred_proba >= threshold).astype(int)
    auc = roc_auc_score(y_true, y_pred_proba)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    cm = confusion_matrix(y_true, y_pred)
    return {"auc": float(auc), "precision": float(prec), "recall": float(rec), "confusion_matrix": cm.tolist()}

def profit_factor_retained(df_test, y_pred_proba, threshold, pips_col="pips"):
    mask = y_pred_proba >= threshold
    retained = df_test[mask]
    if len(retained) == 0:
        return np.nan, 0, 0
    gains = retained[pips_col][retained[pips_col] > 0].sum()
    losses = retained[pips_col][retained[pips_col] < 0].sum()
    pf = float(gains / abs(losses)) if losses < 0 else np.inf
    return pf, len(retained), float(retained[pips_col].sum())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features-parquet", default=os.path.join("data","features","trades_features.parquet"))
    ap.add_argument("--out-dir", default="ml/models")
    ap.add_argument("--reports-dir", default="ml/reports")
    args = ap.parse_args()

    Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    Path(os.path.join(args.out_dir, "metadata")).mkdir(parents=True, exist_ok=True)
    Path(args.reports_dir).mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(args.features_parquet)
    # Drop non-feature cols
    excl = ["pips", "label_win", "date", "sec_session"]
    feature_cols = [c for c in df.columns if c not in excl]
    X = df[feature_cols].fillna(df[feature_cols].median())
    y = df["label_win"].astype(int)

    # Time split
    train, val, test = time_split(df, train_pct=0.70, val_pct=0.15)
    save_splits(train, val, test)

    # Fillna: median first, then 0 for all-NaN columns (ATR, EMA features might be NaN)
    X_train = train[feature_cols].fillna(train[feature_cols].median()).fillna(0)
    y_train = train["label_win"].astype(int)
    X_val = val[feature_cols].fillna(val[feature_cols].median()).fillna(0)
    y_val = val["label_win"].astype(int)
    X_test = test[feature_cols].fillna(test[feature_cols].median()).fillna(0)
    y_test = test["label_win"].astype(int)

    print(f"Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")

    # Logistic Regression
    lr = LogisticRegression(random_state=42, max_iter=500)
    lr.fit(X_train, y_train)
    lr_val_proba = lr.predict_proba(X_val)[:,1]
    lr_test_proba = lr.predict_proba(X_test)[:,1]
    lr_val_metrics = compute_metrics(y_val, lr_val_proba)
    lr_test_metrics = compute_metrics(y_test, lr_test_proba)

    lr_model_path = os.path.join(args.out_dir, "trade_quality_lr.pkl")
    with open(lr_model_path, "wb") as f:
        pickle.dump(lr, f)

    lr_meta = {
        "model_name": "trade_quality_lr",
        "model_type": "Logistic Regression",
        "training_date": datetime.now().isoformat(),
        "features_used": feature_cols,
        "label": "label_win (pips > 0)",
        "train_rows": len(train),
        "val_rows": len(val),
        "test_rows": len(test),
        "val_metrics": lr_val_metrics,
        "test_metrics": lr_test_metrics,
    }
    lr_meta_path = os.path.join(args.out_dir, "metadata", "trade_quality_lr_meta.json")
    with open(lr_meta_path, "w") as f:
        json.dump(lr_meta, f, indent=2)

    print(f"✅ Logistic Regression trained: Val AUC={lr_val_metrics['auc']:.3f}, Test AUC={lr_test_metrics['auc']:.3f}")

    # LightGBM (optional)
    if HAS_LGB:
        gbm = lgb.LGBMClassifier(num_leaves=31, learning_rate=0.05, n_estimators=100, random_state=42)
        gbm.fit(X_train, y_train, eval_set=[(X_val, y_val)], eval_metric="auc")
        gbm_val_proba = gbm.predict_proba(X_val)[:,1]
        gbm_test_proba = gbm.predict_proba(X_test)[:,1]
        gbm_val_metrics = compute_metrics(y_val, gbm_val_proba)
        gbm_test_metrics = compute_metrics(y_test, gbm_test_proba)

        gbm_model_path = os.path.join(args.out_dir, "trade_quality_gbm.pkl")
        with open(gbm_model_path, "wb") as f:
            pickle.dump(gbm, f)

        # Feature importance
        importance = pd.DataFrame({"feature": feature_cols, "gain": gbm.booster_.feature_importance(importance_type="gain")})
        importance = importance.sort_values("gain", ascending=False)
        importance.to_csv(os.path.join(args.reports_dir, "feature_importance_gbm.csv"), index=False)

        gbm_meta = {
            "model_name": "trade_quality_gbm",
            "model_type": "LightGBM Classifier",
            "training_date": datetime.now().isoformat(),
            "features_used": feature_cols,
            "label": "label_win (pips > 0)",
            "train_rows": len(train),
            "val_rows": len(val),
            "test_rows": len(test),
            "hyperparameters": {"num_leaves":31, "learning_rate":0.05, "n_estimators":100},
            "val_metrics": gbm_val_metrics,
            "test_metrics": gbm_test_metrics,
            "feature_importance_top5": importance.head(5).to_dict(orient="records"),
        }
        gbm_meta_path = os.path.join(args.out_dir, "metadata", "trade_quality_gbm_meta.json")
        with open(gbm_meta_path, "w") as f:
            json.dump(gbm_meta, f, indent=2)

        print(f"✅ LightGBM trained: Val AUC={gbm_val_metrics['auc']:.3f}, Test AUC={gbm_test_metrics['auc']:.3f}")
        print(f"   Feature importance saved: {os.path.join(args.reports_dir, 'feature_importance_gbm.csv')}")
    else:
        print("⚠️ LightGBM not installed; skipping GBM training.")

    print(f"✅ Models and metadata saved to {args.out_dir}")

if __name__ == "__main__":
    main()
