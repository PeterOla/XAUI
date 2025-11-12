"""
Univariate feature analysis: mutual information, correlation, AUC, quantile PF.
Phase 3A research to determine which features (primary vs secondary) are most predictive.
"""
import argparse
import os
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif
from sklearn.metrics import roc_auc_score

def profit_factor(pips: pd.Series):
    gains = pips[pips > 0].sum()
    losses = pips[pips < 0].sum()
    return float(gains / abs(losses)) if losses < 0 else np.inf

def univariate_auc(x: pd.Series, y: pd.Series):
    # Normalize x to [0,1] for a crude univariate score
    x = (x - x.min()) / (x.max() - x.min() + 1e-12)
    try:
        return roc_auc_score(y, x)
    except Exception:
        return np.nan

def summarize_by_quantiles(df, feature, label_col="label_win", pips_col="pips", q=5):
    try:
        bins = pd.qcut(df[feature], q=q, duplicates="drop")
    except Exception:
        return None
    out = []
    for b, grp in df.groupby(bins):
        if grp.empty: continue
        out.append({
            "feature": feature,
            "bin": str(b),
            "count": len(grp),
            "win_rate": float(grp[label_col].mean()),
            "pf": profit_factor(grp[pips_col]),
            "avg_pips": float(grp[pips_col].mean()),
        })
    return pd.DataFrame(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features-parquet", default=os.path.join("data","features","trades_features.parquet"))
    ap.add_argument("--out-dir", default=os.path.join("results","ml"))
    args = ap.parse_args()

    Path(args.out_dir).mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(args.features_parquet)
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c not in ("label_win","pips","date")]
    y = df["label_win"].astype(int)

    # Fill NaN: chained fillna to handle all-NaN columns
    X_filled = df[num_cols].fillna(df[num_cols].median()).fillna(0)

    # Mutual information and correlation
    mi = mutual_info_classif(X_filled, y, random_state=42)
    mi_tbl = pd.DataFrame({"feature": num_cols, "mutual_info": mi})
    corr_tbl = pd.DataFrame({"feature": num_cols, "corr": [np.corrcoef(X_filled[c], y)[0,1] for c in num_cols]})
    auc_tbl = pd.DataFrame({"feature": num_cols, "auc": [univariate_auc(X_filled[c], y) for c in num_cols]})

    # Merge
    summary = mi_tbl.merge(corr_tbl, on="feature").merge(auc_tbl, on="feature")
    summary["is_secondary"] = summary["feature"].str.startswith("sec_")
    summary = summary.sort_values("mutual_info", ascending=False)

    # Quantile PF per feature (top 25 by MI only)
    qrows = []
    for f in summary.head(25)["feature"]:
        qt = summarize_by_quantiles(df[[f,"label_win","pips"]].dropna(), f, "label_win", "pips", q=5)
        if qt is not None:
            qt["is_secondary"] = f.startswith("sec_")
            qrows.append(qt)
    qsummary = pd.concat(qrows, ignore_index=True) if qrows else pd.DataFrame()

    # Session PF table (sanity check for secondary features)
    sess_cols = ["sec_is_asia","sec_is_london","sec_is_overlap","sec_is_ny_late","sec_is_off"]
    sess_rows = []
    for sc in sess_cols:
        if sc in df.columns:
            grp = df[df[sc] == 1]
            if len(grp) > 0:
                sess_rows.append({
                    "session_flag": sc,
                    "count": len(grp),
                    "win_rate": float(grp["label_win"].mean()),
                    "pf": profit_factor(grp["pips"]),
                    "avg_pips": float(grp["pips"].mean())
                })
    sess_tbl = pd.DataFrame(sess_rows)

    # Save
    summary_path = os.path.join(args.out_dir, "features_univariate_summary.csv")
    qsummary_path = os.path.join(args.out_dir, "features_quantile_pf.csv")
    session_path = os.path.join(args.out_dir, "session_pf.csv")
    summary.to_csv(summary_path, index=False)
    if not qsummary.empty: qsummary.to_csv(qsummary_path, index=False)
    if not sess_tbl.empty: sess_tbl.to_csv(session_path, index=False)

    # MD report
    md_path = os.path.join(args.out_dir, "features_univariate_summary.md")
    with open(md_path, "w") as f:
        f.write("# Feature Univariate Summary\n\n")
        f.write(f"- Rows: {len(df)}\n")
        f.write(f"- Primary vs Secondary: {int((~summary['is_secondary']).sum())} / {int(summary['is_secondary'].sum())}\n\n")
        f.write("## Top 20 by Mutual Information\n\n")
        f.write(summary.head(20).to_markdown(index=False))
        if not sess_tbl.empty:
            f.write("\n\n## Session PF\n\n")
            f.write(sess_tbl.to_markdown(index=False))
        if not qsummary.empty:
            f.write("\n\n## Quantile PF (top features)\n\n")
            f.write(qsummary.head(50).to_markdown(index=False))

    print(f"✅ Wrote: {summary_path}")
    if os.path.exists(qsummary_path): print(f"✅ Wrote: {qsummary_path}")
    if os.path.exists(session_path): print(f"✅ Wrote: {session_path}")
    print(f"✅ Wrote: {md_path}")

if __name__ == "__main__":
    main()
