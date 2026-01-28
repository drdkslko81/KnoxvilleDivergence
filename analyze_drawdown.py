import pandas as pd

fn = r"c:\AlgoSafeCodeStreamlit\backtest_trades.csv"
df = pd.read_csv(fn, parse_dates=["ExitDate", "EntryDate"]) 

# Drawdown period from previous analysis
peak = pd.Timestamp("2022-01-17")
trough = pd.Timestamp("2022-06-23")

mask = (df['ExitDate'] >= peak) & (df['ExitDate'] <= trough)
df_period = df.loc[mask].copy()

if df_period.empty:
    print("No trades in drawdown period")
    raise SystemExit(0)

total = len(df_period)
wins = (df_period['ProfitLoss'] > 0).sum()
losses = (df_period['ProfitLoss'] <= 0).sum()
win_rate = wins / total * 100

sum_loss = df_period[df_period['ProfitLoss'] < 0]['ProfitLoss'].sum()
sum_win = df_period[df_period['ProfitLoss'] > 0]['ProfitLoss'].sum()
profit_factor = (sum_win / abs(sum_loss)) if abs(sum_loss) > 0 else float('inf')

avg_loss = df_period[df_period['ProfitLoss'] < 0]['ProfitLoss'].mean()
avg_win = df_period[df_period['ProfitLoss'] > 0]['ProfitLoss'].mean()
avg_loss_pct = df_period[df_period['ProfitLossPct'] < 0]['ProfitLossPct'].mean()

# Count large fixed losses (e.g. ~-9999.9)
large_losses = df_period[ df_period['ProfitLoss'] <= -9000 ]
large_loss_count = len(large_losses)
large_loss_pct = large_loss_count / total * 100

# Exit types
exit_counts = df_period['ExitType'].value_counts()

# Top losing symbols
top_losers = df_period.groupby('Symbol')['ProfitLoss'].sum().sort_values().head(10)

# Holding period
avg_holding = df_period['HoldingPeriod'].mean()

print(f"Drawdown period trades: {total}")
print(f"Wins: {wins}, Losses: {losses}, Win rate: {win_rate:.1f}%")
print(f"Sum wins: {sum_win:,.0f}  Sum losses: {sum_loss:,.0f}")
print(f"Profit factor in period: {profit_factor:.2f}")
print(f"Avg win: {avg_win:,.2f}  Avg loss: {avg_loss:,.2f}  Avg loss %: {avg_loss_pct:.2f}%")
print(f"Avg holding period (days): {avg_holding:.1f}")
print(f"Large fixed losses (<= -9000): {large_loss_count} ({large_loss_pct:.1f}%)")
print('\nExit type counts:')
print(exit_counts)
print('\nTop 10 losing symbols (by total P&L):')
print(top_losers)

print('\nSample top 10 largest losing trades in period:')
print(df_period.sort_values('ProfitLoss').head(10)[['EntryDate','ExitDate','Symbol','EntryPrice','ExitPrice','ProfitLoss','ProfitLossPct','ExitType','HoldingPeriod']])
