import pandas as pd
from datetime import datetime

fn = r"c:\AlgoSafeCodeStreamlit\backtest_trades.csv"
try:
    df = pd.read_csv(fn, parse_dates=["ExitDate", "EntryDate"]) 
except Exception as e:
    print("ERROR reading CSV:", e)
    raise

if df.empty:
    print("No trades found")
    raise SystemExit(0)

# Basic stats
initial_capital = 1000000.0
total_trades = len(df)
wins = (df['ProfitLoss'] > 0).sum()
win_rate = wins / total_trades * 100
mean_pnl_pct = df['ProfitLossPct'].mean()
median_pnl_pct = df['ProfitLossPct'].median()
total_pnl = df['ProfitLoss'].sum()
avg_pnl = df['ProfitLoss'].mean()

# Equity curve by exit date
df_sorted = df.sort_values('ExitDate')
equity = (df_sorted['ProfitLoss'].cumsum() + initial_capital)

dates = pd.to_datetime(df_sorted['ExitDate'])
start = dates.min()
end = dates.max()
days = (end - start).days if pd.notnull(start) and pd.notnull(end) else 0

years = days / 365.0 if days > 0 else 0
final_equity = equity.iloc[-1]

cagr = ((final_equity / initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0

# Max drawdown
cum = equity
running_max = cum.cummax()
drawdown = (running_max - cum) / running_max
max_dd = drawdown.max() * 100

# Profit factor (sum wins / abs(sum losses))
sum_wins = df[df['ProfitLoss']>0]['ProfitLoss'].sum()
sum_losses = df[df['ProfitLoss']<0]['ProfitLoss'].sum()
profit_factor = (sum_wins / abs(sum_losses)) if abs(sum_losses) > 0 else float('inf')

print(f"Total Trades: {total_trades}")
print(f"Wins: {wins}  Win Rate: {win_rate:.1f}%")
print(f"Total PnL (₹): {total_pnl:,.0f}")
print(f"Final Equity (₹): {final_equity:,.0f}")
print(f"CAGR: {cagr:.2f}% over {days} days")
print(f"Avg PnL per trade (₹): {avg_pnl:,.2f}")
print(f"Avg PnL % per trade: {mean_pnl_pct:.2f}%  Median: {median_pnl_pct:.2f}%")
print(f"Profit Factor: {profit_factor:.2f}")
print(f"Max Drawdown: {max_dd:.1f}%")

# Basic distribution
print('\nSample top 5 winning trades:')
print(df.sort_values('ProfitLoss', ascending=False).head(5)[['EntryDate','ExitDate','Symbol','ProfitLoss','ProfitLossPct']])
print('\nSample top 5 losing trades:')
print(df.sort_values('ProfitLoss').head(5)[['EntryDate','ExitDate','Symbol','ProfitLoss','ProfitLossPct']])

# Find peak (before trough) and trough dates for max drawdown
cum_series = equity.reset_index(drop=True)
drawdown_series = drawdown.reset_index(drop=True)
if not drawdown_series.empty:
    trough_pos = int(drawdown_series.idxmax())
    trough_date = df_sorted.iloc[trough_pos]['ExitDate']
    peak_pos = int(cum_series[:trough_pos+1].idxmax())
    peak_date = df_sorted.iloc[peak_pos]['ExitDate']
    peak_value = float(cum_series.iloc[peak_pos])
    trough_value = float(cum_series.iloc[trough_pos])
    dd_pct = drawdown_series.iloc[trough_pos] * 100
    print('\nMax Drawdown Details:')
    print(f"Peak Date: {peak_date.strftime('%Y-%m-%d')}  Peak Equity: ₹{peak_value:,.0f}")
    print(f"Trough Date: {trough_date.strftime('%Y-%m-%d')}  Trough Equity: ₹{trough_value:,.0f}")
    print(f"Drawdown: {dd_pct:.1f}% from peak to trough")
