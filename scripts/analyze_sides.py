import pandas as pd

df = pd.read_csv('results/baseline_2015_2025_up_both_full/15m/trades_simple.csv')

print('=== Side Breakdown ===')
print(df['side'].value_counts())

print('\n=== Performance by Side ===')
for side in ['long', 'short']:
    side_df = df[df['side'] == side]
    winners = (side_df['pips'] > 0).sum()
    win_rate = winners / len(side_df) * 100
    
    gains = side_df[side_df['pips'] > 0]['pips'].sum()
    losses = side_df[side_df['pips'] < 0]['pips'].sum()
    pf = gains / abs(losses) if losses < 0 else float('inf')
    
    print(f'\n{side.upper()}:')
    print(f'  Trades: {len(side_df)}')
    print(f'  Win Rate: {win_rate:.1f}%')
    print(f'  Profit Factor: {pf:.2f}')
    print(f'  Avg Trade: {side_df["pips"].mean():.1f} pips')
    print(f'  Total Pips: {side_df["pips"].sum():.1f}')
