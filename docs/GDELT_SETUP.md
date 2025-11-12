# GDELT News + Sentiment Analysis Setup

## Overview

This pipeline fetches real-time news headlines from GDELT and analyzes their sentiment using HuggingFace's FinBERT model to improve trading decisions.

## Quick Start

### 1. Install Dependencies

```powershell
# Install required packages
pip install -r requirements_sentiment.txt

# This installs:
# - transformers (HuggingFace)
# - torch (PyTorch for ML models)
# - requests (GDELT API)
# - pandas, numpy, pyarrow
```

**Note:** Default installs CPU-only PyTorch. For GPU acceleration (much faster):
```powershell
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### 2. Run Full Pipeline (Automated)

```powershell
# Fetch ALL 2,490 trade windows + analyze sentiment (~15-20 minutes)
python run_gdelt_pipeline.py --all

# Or fetch only (skip sentiment analysis)
python run_gdelt_pipeline.py --fetch-only

# Or analyze existing headlines (skip fetching)
python run_gdelt_pipeline.py --analyze-only
```

### 3. Manual Step-by-Step (Optional)

If you want more control:

```powershell
# Step 1: Fetch headlines from GDELT (~12-15 minutes for 2,490 trades)
python sentiments/fetch_news_gdelt.py `
  --events-csv sentiments/news/events_offline.csv `
  --out-csv sentiments/news/headlines_raw.csv `
  --max-events -1 `
  --throttle-sec 0.3

# Step 2: Analyze sentiment with FinBERT (~5-10 minutes)
python scripts/ml/analyze_gdelt_sentiment.py `
  --headlines-csv sentiments/news/headlines_raw.csv `
  --events-csv sentiments/news/events_offline.csv `
  --out-parquet data/features/trades_sentiment_gdelt.parquet `
  --model ProsusAI/finbert `
  --batch-size 32 `
  --device cpu
```

## What It Does

### Phase 1: GDELT Headline Fetching

**Input:** `sentiments/news/events_offline.csv` (2,490 trade windows with 3-hour lookback)

**Process:**
- Queries GDELT Doc API for each trade window
- Search query: "gold OR xau OR bullion OR inflation OR yields OR fed OR cpi OR nfp"
- Fetches up to 250 headlines per window
- Throttles requests (0.3 sec between calls)
- Filters English-language articles only

**Output:** `sentiments/news/headlines_raw.csv`
- Expected: 50K-150K headlines (~20-60 per trade)
- Columns: timestamp, title, url, sourcecountry, lang, event_index, entry_time

**Runtime:** ~12-15 minutes (2,490 API calls × 0.3s throttling)

### Phase 2: Sentiment Analysis

**Input:** `sentiments/news/headlines_raw.csv`

**Process:**
- Loads FinBERT model (financial sentiment specialist)
- Classifies each headline: bullish/bearish/neutral for gold
- Applies context-aware mapping:
  - "Inflation surge" → gold bullish (safe haven demand)
  - "Rate hike" → gold bearish (dollar strength)
  - "Dollar weakness" → gold bullish
  - "Risk-off" → gold bullish
- Aggregates sentiment per trade window

**Output:** `data/features/trades_sentiment_gdelt.parquet`

**Features extracted (12 per trade):**
1. `headline_count` — Total headlines in 3-hour window
2. `bullish_count` — Headlines classified as gold-bullish
3. `bearish_count` — Headlines classified as gold-bearish
4. `neutral_count` — Neutral sentiment headlines
5. `net_sentiment` — (bullish - bearish) / total, range [-1, +1]
6. `avg_sentiment_score` — Average confidence across all headlines
7. `max_bullish_score` — Strongest bullish signal detected
8. `max_bearish_score` — Strongest bearish signal detected
9. `sentiment_volatility` — Std dev of sentiment (how mixed)
10. `gold_mention_count` — Headlines explicitly mentioning "gold"/"xau"
11. `gold_mention_pct` — % of headlines mentioning gold
12. `event_index` — Links back to trade

**Runtime:** ~5-10 minutes (depends on CPU/GPU)

## Expected Results

### Coverage
- **Current (111 manual events):** 140 trades (5.6%) with news
- **Expected (GDELT):** 500-1,000 trades (20-40%) with ≥5 headlines

### Filter Strategy
Apply filters to trade only during high-news periods:
- `headline_count ≥ 5` — Sufficient news coverage
- `|net_sentiment| > 0.3` — Clear directional bias
- `gold_mention_count ≥ 2` — Gold explicitly in focus

### Performance Target
- **Baseline:** PF 1.13, WR 35-40%
- **Manual news filter (test):** PF 2.635, WR 66.7%, but only 9 trades
- **GDELT target:** ≥20 test trades, PF ≥1.25, WR ≥38%

## Sentiment Classification Logic

FinBERT outputs: positive/negative/neutral

We map to **gold-specific sentiment**:

### Gold Bullish (Safe Haven Demand)
- Inflation concerns, rate cuts, QE announcements
- Dollar weakness, yields falling
- Risk-off sentiment, geopolitical tension
- Banking crises, recession fears
- Fed dovish pivot

### Gold Bearish (Risk-On / Dollar Strength)
- Rate hikes, hawkish Fed
- Dollar strength, yields rising
- Risk-on sentiment, strong economy
- Disinflation, tapering announcements

### Context-Aware Examples
| Headline | FinBERT | Gold Sentiment | Reasoning |
|----------|---------|----------------|-----------|
| "Inflation surges to 40-year high" | Negative | **Bullish** | Bad for economy → safe haven demand |
| "Fed cuts rates by 50 bps" | Positive | **Bullish** | Lower rates → gold attractive |
| "Dollar index rallies to 2-year high" | Positive | **Bearish** | Strong dollar = weak gold |
| "Yields jump on strong jobs data" | Positive | **Bearish** | Opportunity cost for gold |
| "Risk-off trade amid banking crisis" | Negative | **Bullish** | Flight to safety |

## Files Created

### Core Pipeline
- `run_gdelt_pipeline.py` — Master orchestration script
- `requirements_sentiment.txt` — Package dependencies
- `sentiments/fetch_news_gdelt.py` — GDELT API client (already existed)
- `scripts/ml/analyze_gdelt_sentiment.py` — FinBERT sentiment analyzer (NEW)

### Data Flow
```
events_offline.csv (2,490 trades)
    ↓ fetch_news_gdelt.py
headlines_raw.csv (50K-150K headlines)
    ↓ analyze_gdelt_sentiment.py
trades_sentiment_gdelt.parquet (2,490 trades × 12 features)
    ↓ merge with technical features
trades_features_combined.parquet (2,490 trades × 50+ features)
    ↓ backtest_news_filter.py
DEPLOYMENT (if gates pass)
```

## Troubleshooting

### "Import transformers could not be resolved"
```powershell
pip install transformers torch
```

### "CUDA out of memory" (if using GPU)
Reduce batch size:
```powershell
python scripts/ml/analyze_gdelt_sentiment.py --batch-size 8 --device cuda
```

### "Too many requests" from GDELT
Increase throttle:
```powershell
python sentiments/fetch_news_gdelt.py --throttle-sec 0.5
```

### Missing events_offline.csv
Create event windows first:
```powershell
python scripts/ml/create_gdelt_events.py
```

## Next Steps After Pipeline

1. **Merge with trade data:**
   ```python
   import pandas as pd
   trades = pd.read_csv("results/.../trades.csv")
   sentiment = pd.read_parquet("data/features/trades_sentiment_gdelt.parquet")
   merged = trades.merge(sentiment, on="event_index")
   ```

2. **Apply filters:**
   ```python
   filtered = merged[
       (merged["headline_count"] >= 5) &
       (merged["net_sentiment"].abs() > 0.3)
   ]
   ```

3. **Backtest:**
   ```powershell
   python scripts/ml/backtest_news_filter.py `
     --features-parquet data/features/trades_features_with_gdelt.parquet
   ```

4. **Validate gates:**
   - Test trades ≥ 20
   - Test PF ≥ 1.25
   - Test WR ≥ 38%

5. **Deploy if successful**

## Performance Notes

### CPU vs GPU
- **CPU:** ~10-15 minutes for sentiment analysis (acceptable)
- **GPU:** ~2-3 minutes (recommended if available)

### Memory Usage
- Headlines CSV: ~50-100 MB
- Model loading: ~400-500 MB RAM
- Peak processing: ~1-2 GB RAM

### GDELT API Limits
- No official rate limit
- Recommended throttle: 0.3-0.5 seconds
- Respectful usage prevents blocking

## Model Information

**FinBERT:** `ProsusAI/finbert`
- Trained on financial text (TRC2, Reuters, corporate reports)
- Optimized for financial sentiment (not generic sentiment)
- 3-class output: positive, negative, neutral
- Better than general BERT for financial news

**Alternative models:**
- `distilbert-base-uncased-finetuned-sst-2-english` (generic, faster)
- `cardiffnlp/twitter-roberta-base-sentiment` (social media)
- `yiyanghkust/finbert-tone` (alternative financial BERT)

To use alternative:
```powershell
python scripts/ml/analyze_gdelt_sentiment.py --model distilbert-base-uncased-finetuned-sst-2-english
```

## References

- **GDELT Project:** https://www.gdeltproject.org/
- **GDELT Doc API:** https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- **FinBERT Paper:** https://arxiv.org/abs/1908.10063
- **HuggingFace Transformers:** https://huggingface.co/docs/transformers
