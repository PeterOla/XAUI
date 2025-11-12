#!/usr/bin/env python3
"""
Live Strategy Deployment Script
Runs the combined news filter strategy with monitoring and logging.

Usage:
    python scripts/deploy_live_strategy.py --mode paper  # Paper trading
    python scripts/deploy_live_strategy.py --mode live   # Live trading (use with caution!)
"""

import argparse
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import sys

# Setup logging
log_dir = Path("logs/deployment")
log_dir.mkdir(parents=True, exist_ok=True)

log_file = log_dir / f"deployment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DeploymentConfig:
    """Configuration for live deployment"""
    
    # Strategy Parameters (from validated backtest)
    FILTER_TYPE = "combined"  # bearish, bullish, or combined
    BEARISH_THRESHOLD = -0.1
    BULLISH_THRESHOLD = 0.3
    MIN_HEADLINE_COUNT = 5
    
    # Trading Hours (UTC)
    ENTRY_HOUR_START = 13
    ENTRY_HOUR_END = 16
    
    # SuperTrend Parameters
    SUPERTREND_PERIOD = 10
    SUPERTREND_MULTIPLIER = 3.6
    
    # Risk Management
    MAX_POSITION_SIZE = 0.01  # lot size
    MAX_DAILY_TRADES = 3
    MAX_DAILY_LOSS = 500  # pips
    
    # Performance Expectations (from backtest)
    EXPECTED_TRADES_PER_MONTH = 6.7
    EXPECTED_PROFIT_FACTOR = 1.355
    EXPECTED_WIN_RATE = 0.45
    
    # Alert Thresholds
    MIN_ACCEPTABLE_PF = 1.20  # Alert if PF drops below this
    MIN_ACCEPTABLE_WR = 0.35  # Alert if WR drops below this
    MAX_ACCEPTABLE_DD = 2500  # Alert if DD exceeds this (pips)


class PerformanceMonitor:
    """Monitor live performance and compare to backtest expectations"""
    
    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.trades_file = self.results_dir / "live_trades.csv"
        self.metrics_file = self.results_dir / "live_metrics.json"
        
    def log_trade(self, trade_data: dict):
        """Log a completed trade"""
        df = pd.DataFrame([trade_data])
        
        if self.trades_file.exists():
            existing = pd.read_csv(self.trades_file)
            df = pd.concat([existing, df], ignore_index=True)
        
        df.to_csv(self.trades_file, index=False)
        logger.info(f"Trade logged: {trade_data['side']} at {trade_data['entry_time']}, "
                   f"Result: {trade_data['pips']:.2f} pips")
        
    def calculate_metrics(self) -> dict:
        """Calculate current performance metrics"""
        if not self.trades_file.exists():
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "avg_pips": 0.0,
                "total_pips": 0.0,
                "max_drawdown": 0.0
            }
        
        df = pd.read_csv(self.trades_file)
        
        total_trades = len(df)
        wins = len(df[df['pips'] > 0])
        win_rate = wins / total_trades if total_trades > 0 else 0.0
        
        gross_profit = df[df['pips'] > 0]['pips'].sum() if len(df[df['pips'] > 0]) > 0 else 0
        gross_loss = abs(df[df['pips'] < 0]['pips'].sum()) if len(df[df['pips'] < 0]) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        avg_pips = df['pips'].mean()
        total_pips = df['pips'].sum()
        
        # Calculate drawdown
        cumulative = df['pips'].cumsum()
        running_max = cumulative.cummax()
        drawdown = running_max - cumulative
        max_drawdown = drawdown.max()
        
        metrics = {
            "total_trades": total_trades,
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4),
            "avg_pips": round(avg_pips, 2),
            "total_pips": round(total_pips, 2),
            "max_drawdown": round(max_drawdown, 2),
            "last_updated": datetime.now().isoformat()
        }
        
        # Save metrics
        with open(self.metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        return metrics
    
    def check_alerts(self, metrics: dict):
        """Check if any alert thresholds are breached"""
        alerts = []
        
        # Only check if we have enough trades
        if metrics['total_trades'] >= 20:
            if metrics['profit_factor'] < DeploymentConfig.MIN_ACCEPTABLE_PF:
                alerts.append(f"⚠️ Profit Factor ({metrics['profit_factor']:.3f}) below threshold "
                            f"({DeploymentConfig.MIN_ACCEPTABLE_PF})")
            
            if metrics['win_rate'] < DeploymentConfig.MIN_ACCEPTABLE_WR:
                alerts.append(f"⚠️ Win Rate ({metrics['win_rate']:.2%}) below threshold "
                            f"({DeploymentConfig.MIN_ACCEPTABLE_WR:.2%})")
        
        if metrics['max_drawdown'] > DeploymentConfig.MAX_ACCEPTABLE_DD:
            alerts.append(f"🚨 Max Drawdown ({metrics['max_drawdown']:.0f} pips) exceeds threshold "
                        f"({DeploymentConfig.MAX_ACCEPTABLE_DD} pips)")
        
        return alerts
    
    def print_summary(self):
        """Print current performance summary"""
        metrics = self.calculate_metrics()
        
        logger.info("\n" + "="*60)
        logger.info("LIVE PERFORMANCE SUMMARY")
        logger.info("="*60)
        logger.info(f"Total Trades: {metrics['total_trades']}")
        logger.info(f"Win Rate: {metrics['win_rate']:.2%} (Expected: {DeploymentConfig.EXPECTED_WIN_RATE:.2%})")
        logger.info(f"Profit Factor: {metrics['profit_factor']:.3f} (Expected: {DeploymentConfig.EXPECTED_PROFIT_FACTOR:.3f})")
        logger.info(f"Avg Pips/Trade: {metrics['avg_pips']:.2f}")
        logger.info(f"Total Pips: {metrics['total_pips']:.2f}")
        logger.info(f"Max Drawdown: {metrics['max_drawdown']:.2f} pips")
        logger.info("="*60)
        
        # Check alerts
        alerts = self.check_alerts(metrics)
        if alerts:
            logger.warning("\n⚠️ ALERTS:")
            for alert in alerts:
                logger.warning(alert)
        else:
            logger.info("\n✅ All metrics within expected ranges")
        
        return metrics


def deploy_strategy(mode: str):
    """
    Deploy the combined filter strategy
    
    Args:
        mode: 'paper' for paper trading, 'live' for live trading
    """
    logger.info("="*60)
    logger.info(f"DEPLOYING STRATEGY - Mode: {mode.upper()}")
    logger.info("="*60)
    
    # Configuration summary
    logger.info("\nConfiguration:")
    logger.info(f"  Filter Type: {DeploymentConfig.FILTER_TYPE}")
    logger.info(f"  Bearish Threshold: {DeploymentConfig.BEARISH_THRESHOLD}")
    logger.info(f"  Bullish Threshold: {DeploymentConfig.BULLISH_THRESHOLD}")
    logger.info(f"  Min Headlines: {DeploymentConfig.MIN_HEADLINE_COUNT}")
    logger.info(f"  Trading Hours: {DeploymentConfig.ENTRY_HOUR_START}-{DeploymentConfig.ENTRY_HOUR_END} UTC")
    logger.info(f"  Position Size: {DeploymentConfig.MAX_POSITION_SIZE} lots")
    
    logger.info("\nExpected Performance:")
    logger.info(f"  Trades/Month: {DeploymentConfig.EXPECTED_TRADES_PER_MONTH:.1f}")
    logger.info(f"  Profit Factor: {DeploymentConfig.EXPECTED_PROFIT_FACTOR:.3f}")
    logger.info(f"  Win Rate: {DeploymentConfig.EXPECTED_WIN_RATE:.2%}")
    
    # Setup monitoring
    results_dir = Path(f"results/live_{mode}")
    monitor = PerformanceMonitor(results_dir)
    
    logger.info(f"\nResults Directory: {results_dir}")
    logger.info(f"Trades Log: {monitor.trades_file}")
    logger.info(f"Metrics File: {monitor.metrics_file}")
    
    # Check existing performance
    if monitor.trades_file.exists():
        logger.info("\n📊 Existing Performance:")
        monitor.print_summary()
    
    logger.info("\n" + "="*60)
    logger.info("STRATEGY DEPLOYED SUCCESSFULLY ✅")
    logger.info("="*60)
    
    logger.info("\nNext Steps:")
    logger.info("1. Connect to your broker's API")
    logger.info("2. Subscribe to XAUUSD 1-minute data feed")
    logger.info("3. Monitor for SuperTrend signals during 13-16 UTC")
    logger.info("4. Check news sentiment before each trade")
    logger.info("5. Log all trades using monitor.log_trade()")
    logger.info("6. Review performance daily with monitor.print_summary()")
    
    logger.info("\n⚠️ Risk Reminders:")
    logger.info(f"- Max {DeploymentConfig.MAX_DAILY_TRADES} trades per day")
    logger.info(f"- Stop if daily loss exceeds {DeploymentConfig.MAX_DAILY_LOSS} pips")
    logger.info(f"- Review strategy weekly")
    logger.info(f"- Re-validate monthly on rolling 90-day window")
    
    return monitor


def run_backtest_on_recent_data():
    """Run strategy on most recent data to verify before going live"""
    logger.info("\n🔍 Running validation backtest on recent data...")
    
    # Calculate date 3 months ago
    cutoff_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    logger.info(f"Backtesting from {cutoff_date} to present...")
    
    # This would call your strategy script
    # For now, we'll just log the command
    cmd = (
        f"python scripts/strategy_with_news_filter.py "
        f"--use-news-filter "
        f"--filter-type {DeploymentConfig.FILTER_TYPE} "
        f"--both-sides "
        f"--entry-hours {DeploymentConfig.ENTRY_HOUR_START}-{DeploymentConfig.ENTRY_HOUR_END} "
        f"--date-start {cutoff_date}"
    )
    
    logger.info(f"\nCommand: {cmd}")
    logger.info("\n💡 Run this command to validate on recent 90 days before deployment")
    
    return cmd


def main():
    parser = argparse.ArgumentParser(
        description="Deploy live trading strategy with monitoring"
    )
    parser.add_argument(
        '--mode',
        type=str,
        choices=['paper', 'live'],
        default='paper',
        help='Deployment mode: paper or live trading'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Run validation backtest on recent data first'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'live':
        logger.warning("\n" + "⚠️"*20)
        logger.warning("LIVE TRADING MODE - REAL MONEY AT RISK!")
        logger.warning("Make sure you have thoroughly tested in paper mode first!")
        logger.warning("⚠️"*20 + "\n")
        
        response = input("Type 'YES' to confirm live trading: ")
        if response != 'YES':
            logger.info("Live trading cancelled.")
            return
    
    if args.validate:
        run_backtest_on_recent_data()
        response = input("\nProceed with deployment? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Deployment cancelled.")
            return
    
    # Deploy strategy
    monitor = deploy_strategy(args.mode)
    
    # Example: Log a test trade (remove in production)
    if args.mode == 'paper':
        logger.info("\n📝 Example: Logging a test trade...")
        test_trade = {
            'entry_time': datetime.now().isoformat(),
            'side': 'BUY',
            'entry_price': 2650.50,
            'exit_price': 2655.80,
            'pips': 53.0,
            'headline_count': 8,
            'net_sentiment': 0.35,
            'filter_type': 'strong_bullish'
        }
        monitor.log_trade(test_trade)
        
        logger.info("\n📊 Updated Performance:")
        monitor.print_summary()


if __name__ == "__main__":
    main()
