#!/usr/bin/env python3
"""
Master pipeline to fetch GDELT news and analyze sentiment.

This orchestrates:
1. Fetch headlines from GDELT for all trade windows
2. Analyze sentiment using HuggingFace FinBERT
3. Extract aggregated features per trade
4. Save results for backtesting

Usage:
    python run_gdelt_pipeline.py --all              # Run full pipeline
    python run_gdelt_pipeline.py --fetch-only       # Only fetch headlines
    python run_gdelt_pipeline.py --analyze-only     # Only analyze existing headlines
"""

import argparse
import subprocess
import sys
from pathlib import Path
import time


def run_command(cmd: list, description: str) -> bool:
    """Run a command and report success/failure."""
    print("\n" + "=" * 70)
    print(f"▶️  {description}")
    print("=" * 70)
    print(f"Command: {' '.join(cmd)}\n")
    
    start_time = time.time()
    try:
        result = subprocess.run(cmd, check=True, capture_output=False, text=True)
        elapsed = time.time() - start_time
        print(f"\n✅ {description} completed in {elapsed:.1f} seconds")
        return True
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"\n❌ {description} failed after {elapsed:.1f} seconds")
        print(f"Error: {e}")
        return False


def check_dependencies():
    """Check if required packages are installed."""
    print("\n🔍 Checking dependencies...")
    
    try:
        import pandas
        import requests
        import transformers
        import torch
        print("✅ All core dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("\n📦 Please install requirements:")
        print("   pip install -r requirements_sentiment.txt")
        return False


def main():
    parser = argparse.ArgumentParser(description="GDELT News + Sentiment Pipeline")
    parser.add_argument("--all", action="store_true", 
                       help="Run full pipeline (fetch + analyze)")
    parser.add_argument("--fetch-only", action="store_true",
                       help="Only fetch GDELT headlines")
    parser.add_argument("--analyze-only", action="store_true",
                       help="Only analyze existing headlines")
    parser.add_argument("--max-events", type=int, default=-1,
                       help="Limit number of events to process (-1 for all)")
    parser.add_argument("--skip-dependency-check", action="store_true",
                       help="Skip dependency check")
    
    args = parser.parse_args()
    
    # Default to --all if no flags specified
    if not any([args.all, args.fetch_only, args.analyze_only]):
        args.all = True
    
    print("=" * 70)
    print("🚀 GDELT News + Sentiment Analysis Pipeline")
    print("=" * 70)
    
    # Check dependencies
    if not args.skip_dependency_check:
        if not check_dependencies():
            sys.exit(1)
    
    # Define paths
    base_dir = Path(__file__).parent
    events_csv = base_dir / "sentiments" / "news" / "events_offline.csv"
    headlines_csv = base_dir / "sentiments" / "news" / "headlines_raw.csv"
    sentiment_parquet = base_dir / "data" / "features" / "trades_sentiment_gdelt.parquet"
    
    # Verify events file exists
    if not events_csv.exists():
        print(f"\n❌ Events file not found: {events_csv}")
        print("   Run create_gdelt_events.py first to generate event windows")
        sys.exit(1)
    
    success = True
    
    # Step 1: Fetch headlines from GDELT
    if args.all or args.fetch_only:
        fetch_cmd = [
            sys.executable,
            str(base_dir / "sentiments" / "fetch_news_gdelt.py"),
            "--events-csv", str(events_csv),
            "--out-csv", str(headlines_csv),
            "--max-events", str(args.max_events),
            "--throttle-sec", "0.3",
            "--lang", "English"
        ]
        
        success = run_command(fetch_cmd, "Step 1: Fetching GDELT headlines")
        
        if not success:
            print("\n⚠️  Headline fetching failed. Check errors and retry.")
            if not args.all:
                sys.exit(1)
    
    # Step 2: Analyze sentiment
    if (args.all or args.analyze_only) and success:
        # Check if headlines exist
        if not headlines_csv.exists():
            print(f"\n❌ Headlines file not found: {headlines_csv}")
            print("   Run with --fetch-only first or use --all")
            sys.exit(1)
        
        analyze_cmd = [
            sys.executable,
            str(base_dir / "scripts" / "ml" / "analyze_gdelt_sentiment.py"),
            "--headlines-csv", str(headlines_csv),
            "--events-csv", str(events_csv),
            "--out-parquet", str(sentiment_parquet),
            "--model", "ProsusAI/finbert",
            "--batch-size", "32",
            "--device", "cpu"
        ]
        
        success = run_command(analyze_cmd, "Step 2: Analyzing sentiment with FinBERT")
        
        if not success:
            print("\n⚠️  Sentiment analysis failed. Check errors and retry.")
            sys.exit(1)
    
    # Summary
    print("\n" + "=" * 70)
    if success:
        print("✅ Pipeline completed successfully!")
        print("\n📁 Output files:")
        if headlines_csv.exists():
            print(f"   Headlines: {headlines_csv}")
        if sentiment_parquet.exists():
            print(f"   Sentiment features: {sentiment_parquet}")
        
        print("\n📊 Next steps:")
        print("   1. Review sentiment features in the parquet file")
        print("   2. Merge with trade data for backtesting")
        print("   3. Apply filters (headline_count ≥5, |net_sentiment| >0.3)")
        print("   4. Run backtest_news_filter.py to validate performance")
    else:
        print("⚠️  Pipeline completed with errors. Review logs above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
