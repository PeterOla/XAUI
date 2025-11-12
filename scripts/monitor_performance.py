#!/usr/bin/env python3
"""
Performance Monitoring Dashboard
Tracks live strategy performance and compares to backtest expectations.

Usage:
    python scripts/monitor_performance.py --mode paper
    python scripts/monitor_performance.py --mode live
    python scripts/monitor_performance.py --mode paper --export report.html
"""

import argparse
from pathlib import Path
import pandas as pd
import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_style("darkgrid")


class PerformanceDashboard:
    """Generate performance monitoring dashboard"""
    
    def __init__(self, mode: str):
        self.mode = mode
        self.results_dir = Path(f"results/live_{mode}")
        self.trades_file = self.results_dir / "live_trades.csv"
        self.metrics_file = self.results_dir / "metrics_history.json"
        
        # Backtest benchmarks
        self.benchmarks = {
            'trades_per_month': 6.7,
            'profit_factor': 1.355,
            'win_rate': 0.45,
            'avg_pips': 41.40,
            'max_drawdown': 2079
        }
    
    def load_data(self):
        """Load trade history"""
        if not self.trades_file.exists():
            print(f"❌ No trades file found at {self.trades_file}")
            return None
        
        df = pd.read_csv(self.trades_file)
        df['entry_time'] = pd.to_datetime(df['entry_time'])
        return df
    
    def calculate_metrics(self, df: pd.DataFrame) -> dict:
        """Calculate performance metrics"""
        total_trades = len(df)
        
        if total_trades == 0:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'avg_pips': 0.0,
                'total_pips': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0
            }
        
        wins = len(df[df['pips'] > 0])
        win_rate = wins / total_trades
        
        gross_profit = df[df['pips'] > 0]['pips'].sum()
        gross_loss = abs(df[df['pips'] < 0]['pips'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        avg_pips = df['pips'].mean()
        total_pips = df['pips'].sum()
        
        # Drawdown
        cumulative = df['pips'].cumsum()
        running_max = cumulative.cummax()
        drawdown = running_max - cumulative
        max_drawdown = drawdown.max()
        
        # Sharpe ratio (annualized)
        returns = df['pips']
        sharpe = (returns.mean() / returns.std()) * (252 ** 0.5) if returns.std() > 0 else 0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_pips': avg_pips,
            'total_pips': total_pips,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe
        }
    
    def print_summary(self):
        """Print performance summary with benchmarks"""
        df = self.load_data()
        if df is None or len(df) == 0:
            print("No trades to analyze yet.")
            return
        
        metrics = self.calculate_metrics(df)
        
        # Calculate time period
        first_trade = df['entry_time'].min()
        last_trade = df['entry_time'].max()
        days_trading = (last_trade - first_trade).days + 1
        months_trading = days_trading / 30.0
        
        print("\n" + "="*70)
        print(f"📊 PERFORMANCE DASHBOARD - {self.mode.upper()} MODE")
        print("="*70)
        
        print(f"\n📅 Trading Period:")
        print(f"  First Trade: {first_trade.strftime('%Y-%m-%d')}")
        print(f"  Last Trade:  {last_trade.strftime('%Y-%m-%d')}")
        print(f"  Duration: {days_trading} days ({months_trading:.1f} months)")
        
        print(f"\n📈 Trade Statistics:")
        print(f"  Total Trades: {metrics['total_trades']}")
        print(f"  Trades/Month: {metrics['total_trades'] / months_trading:.1f} "
              f"(Expected: {self.benchmarks['trades_per_month']:.1f})")
        
        print(f"\n💰 Performance Metrics:")
        
        # Win Rate
        wr_diff = (metrics['win_rate'] - self.benchmarks['win_rate']) * 100
        wr_status = "✅" if wr_diff >= 0 else "⚠️"
        print(f"  Win Rate: {metrics['win_rate']:.2%} {wr_status} "
              f"(Expected: {self.benchmarks['win_rate']:.2%}, "
              f"Diff: {wr_diff:+.1f}pp)")
        
        # Profit Factor
        pf_diff = ((metrics['profit_factor'] / self.benchmarks['profit_factor']) - 1) * 100
        pf_status = "✅" if pf_diff >= -10 else "⚠️"
        print(f"  Profit Factor: {metrics['profit_factor']:.3f} {pf_status} "
              f"(Expected: {self.benchmarks['profit_factor']:.3f}, "
              f"Diff: {pf_diff:+.1f}%)")
        
        # Avg Pips
        pips_diff = metrics['avg_pips'] - self.benchmarks['avg_pips']
        pips_status = "✅" if pips_diff >= 0 else "⚠️"
        print(f"  Avg Pips/Trade: {metrics['avg_pips']:.2f} {pips_status} "
              f"(Expected: {self.benchmarks['avg_pips']:.2f}, "
              f"Diff: {pips_diff:+.2f})")
        
        print(f"\n💵 Profit & Loss:")
        print(f"  Total Pips: {metrics['total_pips']:.2f}")
        print(f"  Total P&L (0.01 lot): ${metrics['total_pips'] * 0.10:.2f}")
        print(f"  Total P&L (0.1 lot):  ${metrics['total_pips'] * 1.00:.2f}")
        
        print(f"\n📉 Risk Metrics:")
        dd_pct = (metrics['max_drawdown'] / self.benchmarks['max_drawdown']) * 100
        dd_status = "✅" if dd_pct <= 120 else "🚨"
        print(f"  Max Drawdown: {metrics['max_drawdown']:.2f} pips {dd_status} "
              f"(Expected: {self.benchmarks['max_drawdown']:.0f} pips, "
              f"{dd_pct:.0f}%)")
        print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        
        # Filter breakdown
        print(f"\n🎯 Filter Breakdown:")
        if 'filter_type' in df.columns:
            filter_stats = df.groupby('filter_type').agg({
                'pips': ['count', 'mean', 'sum']
            }).round(2)
            print(filter_stats.to_string())
        
        # Monthly breakdown
        print(f"\n📆 Monthly Performance:")
        df['month'] = df['entry_time'].dt.to_period('M')
        monthly = df.groupby('month').agg({
            'pips': ['count', 'sum', 'mean']
        }).round(2)
        monthly.columns = ['Trades', 'Total Pips', 'Avg Pips']
        print(monthly.to_string())
        
        print("\n" + "="*70)
        
        # Alerts
        alerts = []
        if metrics['total_trades'] >= 20:
            if metrics['profit_factor'] < 1.20:
                alerts.append("🚨 Profit Factor below 1.20 - Strategy may be degrading!")
            if metrics['win_rate'] < 0.35:
                alerts.append("🚨 Win Rate below 35% - Review recent trades!")
        
        if metrics['max_drawdown'] > 2500:
            alerts.append("🚨 Max Drawdown exceeds 2500 pips - Consider reducing position size!")
        
        if alerts:
            print("\n⚠️ ALERTS:")
            for alert in alerts:
                print(f"  {alert}")
        else:
            print("\n✅ All metrics within acceptable ranges")
        
        print("="*70 + "\n")
        
        return metrics
    
    def plot_equity_curve(self, save_path: str = None):
        """Plot equity curve"""
        df = self.load_data()
        if df is None or len(df) == 0:
            return
        
        df = df.sort_values('entry_time')
        df['cumulative_pips'] = df['pips'].cumsum()
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        
        # Equity curve
        ax1.plot(df['entry_time'], df['cumulative_pips'], linewidth=2, color='#2E86AB')
        ax1.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        ax1.set_title(f'Equity Curve - {self.mode.upper()} Mode', fontsize=16, fontweight='bold')
        ax1.set_xlabel('Date', fontsize=12)
        ax1.set_ylabel('Cumulative Pips', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.fill_between(df['entry_time'], 0, df['cumulative_pips'], 
                         where=(df['cumulative_pips'] > 0), alpha=0.3, color='green', label='Profit')
        ax1.fill_between(df['entry_time'], 0, df['cumulative_pips'], 
                         where=(df['cumulative_pips'] <= 0), alpha=0.3, color='red', label='Loss')
        ax1.legend()
        
        # Drawdown
        running_max = df['cumulative_pips'].cummax()
        drawdown = running_max - df['cumulative_pips']
        
        ax2.fill_between(df['entry_time'], 0, -drawdown, color='red', alpha=0.5)
        ax2.set_title('Drawdown', fontsize=16, fontweight='bold')
        ax2.set_xlabel('Date', fontsize=12)
        ax2.set_ylabel('Drawdown (Pips)', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 Chart saved to {save_path}")
        else:
            plt.show()
    
    def generate_report(self, output_file: str = None):
        """Generate HTML report"""
        df = self.load_data()
        if df is None or len(df) == 0:
            print("No trades to report.")
            return
        
        metrics = self.calculate_metrics(df)
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Performance Report - {self.mode.upper()}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
        .container {{ background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #2E86AB; }}
        h2 {{ color: #333; border-bottom: 2px solid #2E86AB; padding-bottom: 10px; }}
        .metric {{ display: inline-block; margin: 15px; padding: 15px; background-color: #f9f9f9; border-radius: 5px; min-width: 200px; }}
        .metric-label {{ font-size: 14px; color: #666; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #2E86AB; }}
        .positive {{ color: green; }}
        .negative {{ color: red; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #2E86AB; color: white; }}
        tr:hover {{ background-color: #f5f5f5; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Performance Report - {self.mode.upper()} Mode</h1>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>Key Metrics</h2>
        <div class="metric">
            <div class="metric-label">Total Trades</div>
            <div class="metric-value">{metrics['total_trades']}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Win Rate</div>
            <div class="metric-value {'positive' if metrics['win_rate'] >= 0.45 else ''}">{metrics['win_rate']:.2%}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Profit Factor</div>
            <div class="metric-value {'positive' if metrics['profit_factor'] >= 1.3 else ''}">{metrics['profit_factor']:.3f}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Total Pips</div>
            <div class="metric-value {'positive' if metrics['total_pips'] > 0 else 'negative'}">{metrics['total_pips']:.2f}</div>
        </div>
        
        <h2>Recent Trades (Last 10)</h2>
        <table>
            <tr>
                <th>Date</th>
                <th>Side</th>
                <th>Entry</th>
                <th>Exit</th>
                <th>Pips</th>
                <th>Sentiment</th>
            </tr>
"""
        
        # Add last 10 trades
        recent = df.sort_values('entry_time', ascending=False).head(10)
        for _, trade in recent.iterrows():
            pips_class = 'positive' if trade['pips'] > 0 else 'negative'
            html += f"""
            <tr>
                <td>{trade['entry_time'].strftime('%Y-%m-%d %H:%M')}</td>
                <td>{trade['side']}</td>
                <td>{trade['entry_price']:.2f}</td>
                <td>{trade['exit_price']:.2f}</td>
                <td class="{pips_class}">{trade['pips']:.2f}</td>
                <td>{trade.get('net_sentiment', 'N/A')}</td>
            </tr>
"""
        
        html += """
        </table>
    </div>
</body>
</html>
"""
        
        if output_file is None:
            output_file = self.results_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        with open(output_file, 'w') as f:
            f.write(html)
        
        print(f"📄 Report saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Monitor strategy performance")
    parser.add_argument('--mode', type=str, choices=['paper', 'live'], required=True)
    parser.add_argument('--plot', action='store_true', help='Generate equity curve plot')
    parser.add_argument('--export', type=str, help='Export report to HTML file')
    
    args = parser.parse_args()
    
    dashboard = PerformanceDashboard(args.mode)
    dashboard.print_summary()
    
    if args.plot:
        plot_file = dashboard.results_dir / f"equity_curve_{datetime.now().strftime('%Y%m%d')}.png"
        dashboard.plot_equity_curve(save_path=plot_file)
    
    if args.export:
        dashboard.generate_report(args.export)


if __name__ == "__main__":
    main()
