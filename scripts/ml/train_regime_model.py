"""
Train daily regime classifier (Phase 3B).
Multi-class: Strong / Neutral / Avoid. Derive regime_score = P(Strong).
"""
import argparse
import os
from pathlib import Path
import pandas as pd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features-parquet", default=os.path.join("data","features","daily_regime_features.parquet"))
    ap.add_argument("--out-model", default=os.path.join("ml","models","day_regime.pkl"))
    args = ap.parse_args()

    Path(os.path.dirname(args.out_model)).mkdir(parents=True, exist_ok=True)

    # TODO: Implement LightGBM multi-class training
    # - Time-based split
    # - Train classifier
    # - Save model + metadata JSON
    # - Output confusion matrix, PF per regime, report MD

    print("⚠️ train_regime_model.py is a stub. Implement daily regime training logic.")

if __name__ == "__main__":
    main()
