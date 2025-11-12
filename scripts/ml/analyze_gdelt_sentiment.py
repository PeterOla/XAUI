#!/usr/bin/env python3
"""
Analyze sentiment of GDELT headlines using HuggingFace transformers.

This script:
1. Loads headlines_raw.csv from GDELT
2. Classifies each headline using FinBERT (financial sentiment model)
3. Aggregates sentiment per trade window (event_index)
4. Outputs sentiment features for each trade

Features extracted per trade:
- headline_count: Total headlines in 3-hour window
- bullish_count: Headlines with positive sentiment
- bearish_count: Headlines with negative sentiment  
- neutral_count: Headlines with neutral sentiment
- net_sentiment: (bullish - bearish) / total
- avg_sentiment_score: Average sentiment confidence
- max_bullish_score: Strongest bullish signal
- max_bearish_score: Strongest bearish signal
- sentiment_volatility: Std dev of sentiment scores
- gold_mention_count: Headlines explicitly mentioning "gold" or "xau"
"""

import argparse
import warnings
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import numpy as np
from tqdm import tqdm

# Suppress transformers warnings
warnings.filterwarnings("ignore")

def parse_args():
    ap = argparse.ArgumentParser(description="Analyze sentiment of GDELT headlines")
    ap.add_argument("--headlines-csv", type=str, required=True,
                    help="Path to headlines_raw.csv from GDELT")
    ap.add_argument("--events-csv", type=str, required=True,
                    help="Path to events_offline.csv with trade info")
    ap.add_argument("--out-parquet", type=str, required=True,
                    help="Output parquet file with sentiment features")
    ap.add_argument("--model", type=str, default="ProsusAI/finbert",
                    choices=["ProsusAI/finbert", "distilbert-base-uncased-finetuned-sst-2-english"],
                    help="HuggingFace model to use for sentiment analysis")
    ap.add_argument("--batch-size", type=int, default=32,
                    help="Batch size for inference")
    ap.add_argument("--device", type=str, default="cpu",
                    choices=["cpu", "cuda"],
                    help="Device to run inference on")
    return ap.parse_args()


def load_sentiment_model(model_name: str, device: str):
    """Load HuggingFace sentiment analysis pipeline."""
    try:
        from transformers import pipeline
    except ImportError:
        raise ImportError(
            "transformers not installed. Run: pip install transformers torch"
        )
    
    print(f"Loading sentiment model: {model_name}")
    print(f"Device: {device}")
    
    # Load pipeline with specified model
    if model_name == "ProsusAI/finbert":
        # FinBERT is specifically trained on financial text
        sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model=model_name,
            device=0 if device == "cuda" else -1,
            truncation=True,
            max_length=512
        )
    else:
        # Generic sentiment model
        sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model=model_name,
            device=0 if device == "cuda" else -1
        )
    
    print("✅ Model loaded successfully")
    return sentiment_pipeline


def classify_headline_gold_sentiment(text: str, sentiment_result: dict) -> dict:
    """
    Classify headline sentiment specifically for gold trading.
    
    FinBERT returns: positive/negative/neutral
    We map to gold-bullish/bearish/neutral based on context.
    
    Gold-bullish indicators:
    - Inflation concerns, rate cuts, dollar weakness, safe haven demand
    - Fed dovish, risk-off, geopolitical tension, banking crisis
    
    Gold-bearish indicators:  
    - Rate hikes, dollar strength, risk-on, yields rising
    - Fed hawkish, strong economy, disinflation
    """
    text_lower = text.lower()
    label = sentiment_result["label"].lower()
    score = sentiment_result["score"]
    
    # Keywords that flip sentiment interpretation for gold
    gold_bullish_keywords = [
        "inflation surge", "inflation shock", "rate cut", "dovish", "easing",
        "dollar weakness", "dollar falls", "safe haven", "risk off", "risk-off",
        "crisis", "uncertainty", "geopolitical", "tension", "war",
        "fed cuts", "fed pause", "banking crisis", "recession fear",
        "yields fall", "yields drop", "qe", "quantitative easing"
    ]
    
    gold_bearish_keywords = [
        "rate hike", "hawkish", "tightening", "dollar strength", "dollar rally",
        "risk on", "risk-on", "yields rise", "yields surge", "yields jump",
        "fed hikes", "strong economy", "disinflation", "inflation cools",
        "tapering", "dollar index up"
    ]
    
    # Check for explicit gold context flippers
    has_bullish_context = any(kw in text_lower for kw in gold_bullish_keywords)
    has_bearish_context = any(kw in text_lower for kw in gold_bearish_keywords)
    
    # Default mapping: positive sentiment = gold bullish (safe haven demand)
    if label in ["positive", "pos"]:
        if has_bearish_context:
            # "Positive" news about dollar strength = bearish for gold
            return {"gold_sentiment": "bearish", "confidence": score}
        else:
            # Generic positive or explicit bullish context
            return {"gold_sentiment": "bullish", "confidence": score}
    
    elif label in ["negative", "neg"]:
        if has_bullish_context:
            # "Negative" news about dollar/yields = bullish for gold
            return {"gold_sentiment": "bullish", "confidence": score}
        else:
            # Generic negative or explicit bearish context
            return {"gold_sentiment": "bearish", "confidence": score}
    
    else:  # neutral
        return {"gold_sentiment": "neutral", "confidence": score}


def analyze_headlines_batch(headlines: List[str], pipeline, batch_size: int) -> List[dict]:
    """Analyze sentiment for a batch of headlines."""
    results = []
    
    # Process in batches for efficiency
    for i in range(0, len(headlines), batch_size):
        batch = headlines[i:i+batch_size]
        try:
            # Get raw sentiment from model
            raw_sentiments = pipeline(batch)
            
            # Map to gold-specific sentiment
            for text, raw_sent in zip(batch, raw_sentiments):
                gold_sent = classify_headline_gold_sentiment(text, raw_sent)
                results.append({
                    "text": text,
                    "raw_label": raw_sent["label"],
                    "raw_score": raw_sent["score"],
                    "gold_sentiment": gold_sent["gold_sentiment"],
                    "confidence": gold_sent["confidence"]
                })
        except Exception as e:
            # Handle errors gracefully
            print(f"Error processing batch: {e}")
            for text in batch:
                results.append({
                    "text": text,
                    "raw_label": "error",
                    "raw_score": 0.0,
                    "gold_sentiment": "neutral",
                    "confidence": 0.0
                })
    
    return results


def extract_sentiment_features(headlines_df: pd.DataFrame, 
                               events_df: pd.DataFrame,
                               pipeline,
                               batch_size: int) -> pd.DataFrame:
    """Extract aggregated sentiment features per trade."""
    
    print("\n📊 Analyzing sentiment for headlines...")
    
    # Filter out error rows
    valid_headlines = headlines_df[~headlines_df["title"].str.startswith("ERROR", na=False)].copy()
    print(f"Valid headlines: {len(valid_headlines):,} / {len(headlines_df):,}")
    
    if valid_headlines.empty:
        print("⚠️ No valid headlines to analyze!")
        return pd.DataFrame()
    
    # Analyze all headlines
    texts = valid_headlines["title"].fillna("").tolist()
    print(f"Processing {len(texts):,} headlines in batches of {batch_size}...")
    
    sentiment_results = []
    for i in tqdm(range(0, len(texts), batch_size), desc="Analyzing sentiment"):
        batch = texts[i:i+batch_size]
        batch_results = analyze_headlines_batch(batch, pipeline, batch_size)
        sentiment_results.extend(batch_results)
    
    # Add sentiment to headlines dataframe
    valid_headlines["gold_sentiment"] = [r["gold_sentiment"] for r in sentiment_results]
    valid_headlines["sentiment_confidence"] = [r["confidence"] for r in sentiment_results]
    valid_headlines["raw_label"] = [r["raw_label"] for r in sentiment_results]
    
    # Check for gold/xau mentions
    valid_headlines["mentions_gold"] = valid_headlines["title"].str.lower().str.contains(
        r"\b(gold|xau|bullion)\b", regex=True, na=False
    )
    
    print("\n📈 Aggregating features per trade...")
    
    # Aggregate by event_index
    features_list = []
    
    for event_idx in tqdm(events_df["event_index"], desc="Computing features"):
        event_headlines = valid_headlines[valid_headlines["event_index"] == event_idx]
        
        if event_headlines.empty:
            # No headlines for this trade
            features_list.append({
                "event_index": event_idx,
                "headline_count": 0,
                "bullish_count": 0,
                "bearish_count": 0,
                "neutral_count": 0,
                "net_sentiment": 0.0,
                "avg_sentiment_score": 0.0,
                "max_bullish_score": 0.0,
                "max_bearish_score": 0.0,
                "sentiment_volatility": 0.0,
                "gold_mention_count": 0,
                "gold_mention_pct": 0.0
            })
            continue
        
        # Count by sentiment
        bullish = (event_headlines["gold_sentiment"] == "bullish").sum()
        bearish = (event_headlines["gold_sentiment"] == "bearish").sum()
        neutral = (event_headlines["gold_sentiment"] == "neutral").sum()
        total = len(event_headlines)
        
        # Compute scores
        bullish_scores = event_headlines[event_headlines["gold_sentiment"] == "bullish"]["sentiment_confidence"]
        bearish_scores = event_headlines[event_headlines["gold_sentiment"] == "bearish"]["sentiment_confidence"]
        
        # Net sentiment: -1 (all bearish) to +1 (all bullish)
        net_sentiment = (bullish - bearish) / total if total > 0 else 0.0
        
        # Average confidence across all headlines
        avg_score = event_headlines["sentiment_confidence"].mean()
        
        # Max scores
        max_bullish = bullish_scores.max() if len(bullish_scores) > 0 else 0.0
        max_bearish = bearish_scores.max() if len(bearish_scores) > 0 else 0.0
        
        # Sentiment volatility (how mixed the sentiment is)
        sentiment_volatility = event_headlines["sentiment_confidence"].std() if total > 1 else 0.0
        
        # Gold mentions
        gold_mentions = event_headlines["mentions_gold"].sum()
        gold_mention_pct = gold_mentions / total if total > 0 else 0.0
        
        features_list.append({
            "event_index": event_idx,
            "headline_count": total,
            "bullish_count": int(bullish),
            "bearish_count": int(bearish),
            "neutral_count": int(neutral),
            "net_sentiment": round(net_sentiment, 4),
            "avg_sentiment_score": round(avg_score, 4),
            "max_bullish_score": round(max_bullish, 4),
            "max_bearish_score": round(max_bearish, 4),
            "sentiment_volatility": round(sentiment_volatility, 4),
            "gold_mention_count": int(gold_mentions),
            "gold_mention_pct": round(gold_mention_pct, 4)
        })
    
    features_df = pd.DataFrame(features_list)
    
    # Merge with events to get entry_time, side, pips
    features_df = features_df.merge(
        events_df[["event_index", "entry_time", "side", "pips"]],
        on="event_index",
        how="left"
    )
    
    print("\n✅ Feature extraction complete!")
    print(f"Trades with headlines: {(features_df['headline_count'] > 0).sum()} / {len(features_df)}")
    print(f"Avg headlines per trade: {features_df['headline_count'].mean():.1f}")
    print(f"Trades with ≥5 headlines: {(features_df['headline_count'] >= 5).sum()}")
    print(f"Trades with ≥10 headlines: {(features_df['headline_count'] >= 10).sum()}")
    
    return features_df


def main():
    args = parse_args()
    
    print("=" * 60)
    print("GDELT Sentiment Analysis Pipeline")
    print("=" * 60)
    
    # Load data
    print("\n📂 Loading data...")
    headlines_df = pd.read_csv(args.headlines_csv)
    events_df = pd.read_csv(args.events_csv)
    
    print(f"Headlines: {len(headlines_df):,}")
    print(f"Events: {len(events_df):,}")
    
    # Load sentiment model
    pipeline = load_sentiment_model(args.model, args.device)
    
    # Extract features
    features_df = extract_sentiment_features(
        headlines_df, 
        events_df, 
        pipeline, 
        args.batch_size
    )
    
    # Save results
    out_path = Path(args.out_parquet)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    features_df.to_parquet(out_path, index=False)
    
    print(f"\n💾 Saved sentiment features to: {out_path}")
    print(f"   Shape: {features_df.shape}")
    print(f"   Columns: {list(features_df.columns)}")
    
    # Summary statistics
    print("\n📊 Summary Statistics:")
    print(features_df[["headline_count", "bullish_count", "bearish_count", 
                       "net_sentiment", "gold_mention_count"]].describe())


if __name__ == "__main__":
    main()
