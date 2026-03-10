import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Swing Trading", layout="wide")

# =========================
# Utilities & Core Logic
# =========================

@st.cache_data(ttl=3600)
def get_nifty50_symbols():
    """Complete Nifty 50 (Jan 2026) - All 50 stocks."""
    return [
        'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'HINDUNILVR.NS',
        'ICICIBANK.NS', 'KOTAKBANK.NS', 'BHARTIARTL.NS', 'ITC.NS', 'SBIN.NS',
        'LT.NS', 'ASIANPAINT.NS', 'AXISBANK.NS', 'MARUTI.NS', 'SUNPHARMA.NS',
        'TITAN.NS', 'DMART.NS', 'ULTRACEMCO.NS', 'NESTLEIND.NS', 'TECHM.NS',
        'HCLTECH.NS', 'POWERGRID.NS', 'NTPC.NS', 'TATAMOTORS.NS', 'JSWSTEEL.NS',
        'WIPRO.NS', 'BAJFINANCE.NS', 'ONGC.NS', 'TATACONSUM.NS', 'TRENT.NS',
        'JIOFIN.NS', 'COALINDIA.NS', 'GRASIM.NS', 'LTIM.NS', 'DRREDDY.NS',
        'ADANIPORTS.NS', 'CIPLA.NS', 'HEROMOTOCO.NS', 'BAJAJFINSV.NS',
        'EICHERMOT.NS', 'APOLLOHOSP.NS', 'DIVISLAB.NS', 'SHRIRAMFIN.NS',
        'BPCL.NS', 'HINDALCO.NS', 'INDUSINDBK.NS', 'BRITANNIA.NS', 'M&M.NS'
    ]


def detect_knoxville_divergence(df, rsi_period=14, mom_period=12, lb=3):
    """Detect bullish/bearish divergence using RSI + pivot points."""
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

    close = df['Close'].squeeze()
    df['RSI'] = ta.momentum.RSIIndicator(close, rsi_period).rsi()
    df['Momentum'] = ta.momentum.ROCIndicator(close, mom_period).roc()
    df['EMA20'] = ta.trend.EMAIndicator(close, 20).ema_indicator()

    df = df.dropna()
    if len(df) < 20:
        df['Buy_Signal'] = 0
        df['Sell_Signal'] = 0
        return df

    def is_pivot_high(series, i, window):
        if i < window or i > len(series) - window - 1:
            return False
        return series.iloc[i] >= series.iloc[i - window:i + window + 1].max()

    def is_pivot_low(series, i, window):
        if i < window or i > len(series) - window - 1:
            return False
        return series.iloc[i] <= series.iloc[i - window:i + window + 1].min()

    df['Buy_Signal'] = 0
    df['Sell_Signal'] = 0

    for i in range(10, len(df)):
        # Bullish divergence / buy
        if (df['RSI'].iloc[i] < 50 and is_pivot_low(df['Close'], i, lb)):
            for j in range(max(0, i - 20), i - 2):
                if is_pivot_low(df['Close'], j, lb):
                    if (df['Close'].iloc[i] < df['Close'].iloc[j] * 1.02 and
                            df['RSI'].iloc[i] > df['RSI'].iloc[j] * 0.95):
                        df.iloc[i, df.columns.get_loc('Buy_Signal')] = 1
                        break

        # Bearish divergence / sell
        if (df['RSI'].iloc[i] > 50 and is_pivot_high(df['Close'], i, lb)):
            for j in range(max(0, i - 20), i - 2):
                if is_pivot_high(df['Close'], j, lb):
                    if (df['Close'].iloc[i] > df['Close'].iloc[j] * 0.98 and
                            df['RSI'].iloc[i] < df['RSI'].iloc[j] * 1.05):
                        df.iloc[i, df.columns.get_loc('Sell_Signal')] = 1
                        break

    return df


@st.cache_data(ttl=3600)
def fetch_data(symbol, start, end):
    """Fetch yfinance data with error handling. yfinance end is exclusive."""
    try:
        data = yf.download(symbol, start=start, end=end, progress=False)
        if data.empty or len(data) < 50:
            return None
        return data
    except Exception:
        return None


def calculate_holding_days(buy_date_str, sell_date_str):
    """Calculate calendar days between buy and sell dates."""
    try:
        buy_date = pd.to_datetime(buy_date_str)
        sell_date = pd.to_datetime(sell_date_str)
        return (sell_date - buy_date).days
    except Exception:
        return 0


# =========================
# Main UI
# =========================

st.title("🔔Swing Trading")
st.markdown("**Nifty 50 scanner**")

tab1, tab2 = st.tabs(["📈 Live Scanner", "⚙️ Backtester"])

# =========================
# TAB 1: Live Scanner
# =========================

with tab1:
    st.header("🔍 Post-Market Signal Scanner")
    uploaded_file = st.file_uploader("Upload stock list (.txt, one per line)", type=['txt'])

    if uploaded_file is not None:
        symbols = [line.decode().strip() for line in uploaded_file.readlines() if line.decode().strip()]
    else:
        symbols = get_nifty50_symbols()
        st.info(f"🔄 Using default Nifty 50 ({len(symbols)} stocks)")

    show_debug = st.toggle("🔧 Show Debug Info", value=False)

    # Freshness mode: only signals on latest bar
    only_latest_bar = st.toggle("✅ Only show signals on latest bar", value=False)

    if st.button("🔍 Scan For Signals", type="primary"):
        signals = []
        progress = st.progress(0)
        debug_container = st.container()

        # For live scan, include today's bar by using end = tomorrow
        today = datetime.today().date()
        scan_start = "2025-01-01"
        scan_end = today + timedelta(days=1)

        for i, symbol in enumerate(symbols):
            try:
                data = fetch_data(symbol, scan_start, scan_end)
                if data is not None and len(data) > 100:
                    signals_df = detect_knoxville_divergence(data.tail(300))

                    if not signals_df.empty:
                        # All signal rows
                        signal_rows = signals_df[(signals_df['Buy_Signal'] == 1) |
                                                 (signals_df['Sell_Signal'] == 1)]

                        if not signal_rows.empty:
                            # Latest signal row in history
                            last_signal_row = signal_rows.iloc[-1]
                            last_signal_date = last_signal_row.name.date()

                            # Latest bar date in data
                            last_bar_date = signals_df.index[-1].date()

                            # Freshness filter
                            if only_latest_bar and last_signal_date != last_bar_date:
                                # Skip older signals
                                pass
                            else:
                                if show_debug:
                                    with debug_container.container():
                                        with st.expander(f"🔍 {symbol} Debug", expanded=False):
                                            st.json({
                                                'Last_Signal_Date': last_signal_date.strftime('%Y-%m-%d'),
                                                'Last_Bar_Date': last_bar_date.strftime('%Y-%m-%d'),
                                                'RSI': f"{float(last_signal_row.get('RSI', 0)):.1f}",
                                                'Price_vs_EMA20': float(last_signal_row.get('Close', 0)) >
                                                                  float(last_signal_row.get('EMA20', 0)),
                                                'Signal_Type': 'BUY' if last_signal_row.get('Buy_Signal', 0) == 1
                                                else 'SELL' if last_signal_row.get('Sell_Signal', 0) == 1
                                                else 'NONE',
                                                'Buy_Signal': int(last_signal_row.get('Buy_Signal', 0)),
                                                'Sell_Signal': int(last_signal_row.get('Sell_Signal', 0)),
                                                'Close_Price': f"₹{float(last_signal_row.get('Close', 0)):.0f}",
                                                'RSI_Condition_Buy': float(last_signal_row.get('RSI', 0)) < 50,
                                            })

                                if last_signal_row['Buy_Signal'] == 1:
                                    signals.append({
                                        'Symbol': symbol,
                                        'Signal': 'BUY',
                                        'Price': float(last_signal_row['Close']),
                                        'RSI': float(last_signal_row['RSI']),
                                        'Signal_Date': last_signal_row.name.strftime('%Y-%m-%d')
                                    })
                                elif last_signal_row['Sell_Signal'] == 1:
                                    signals.append({
                                        'Symbol': symbol,
                                        'Signal': 'SELL',
                                        'Price': float(last_signal_row['Close']),
                                        'RSI': float(last_signal_row['RSI']),
                                        'Signal_Date': last_signal_row.name.strftime('%Y-%m-%d')
                                    })

            except Exception:
                pass

            progress.progress((i + 1) / len(symbols))

        if signals:
            signals_df = pd.DataFrame(signals)
            st.success(f"✅ Found {len(signals)} signals!")
            st.dataframe(signals_df, use_container_width=True)
            csv = signals_df.to_csv(index=False)
            st.download_button("📥 Download Signals CSV", csv, "knoxville_signals.csv")
        else:
            st.info("📊 No fresh signals. Check back after next EOD.")
            if show_debug:
                st.info("🔍 **Debug Summary**: No signals matched the freshness condition.")


# =========================
# TAB 2: Backtester
# =========================

with tab2:
    st.header("📊 Nifty 50 Portfolio Backtester")

    if 'backtest_data' not in st.session_state:
        st.session_state.backtest_data = None
    if 'page' not in st.session_state:
        st.session_state.page = 1

    col1, col2 = st.columns(2)
    with col1:
        symbols = get_nifty50_symbols()
        start_date = st.date_input("Start Date", datetime(2021, 1, 1))
        end_date = st.date_input("End Date", datetime.now())
    with col2:
        initial_capital = st.number_input("Initial Capital (₹)", 1000000, 50000000, 1000000)
        risk_pct = st.slider("Risk per Trade (%)", 0.5, 2.0, 1.0)
        max_positions = st.slider("Max Concurrent Positions", 5, 20, 10)
        max_position_pct = st.slider("Max Position Size (% of capital)", 5.0, 20.0, 10.0)

    if st.button("🚀 Run Backtest", type="primary"):
        with st.spinner("🔄 Running comprehensive backtest..."):
            progress = st.progress(0)

            # STEP 1: Collect ALL raw signals across ALL symbols
            all_raw_signals = []
            successful_symbols = 0

            # Backtest: include end_date's bar, so use end_date + 1
            bt_end = end_date + timedelta(days=1)

            for i, symbol in enumerate(symbols):
                try:
                    data = fetch_data(symbol, start_date, bt_end)
                    if data is None or len(data) < 200:
                        progress.progress((i + 1) / len(symbols))
                        continue

                    signals_df = detect_knoxville_divergence(data.copy())

                    for date in signals_df.index:
                        row = signals_df.loc[date]
                        if row['Buy_Signal'] == 1:
                            all_raw_signals.append({
                                'Symbol': symbol,
                                'Date': date,
                                'Signal': 'BUY',
                                'Open_Price': float(data.loc[date, 'Open'])
                            })
                        elif row['Sell_Signal'] == 1:
                            all_raw_signals.append({
                                'Symbol': symbol,
                                'Date': date,
                                'Signal': 'SELL',
                                'Open_Price': float(data.loc[date, 'Open'])
                            })
                    successful_symbols += 1

                except Exception:
                    pass

                progress.progress((i + 1) / len(symbols))

            # STEP 2: Sort ALL signals chronologically
            all_raw_signals.sort(key=lambda x: x['Date'])
            st.info(f"📊 Collected {len(all_raw_signals)} signals from {successful_symbols} symbols")

            # STEP 3: Process in chronological order
            all_trades = []
            capital = float(initial_capital)
            current_positions = {}

            for signal in all_raw_signals:
                symbol = signal['Symbol']
                date = signal['Date']
                open_price = signal['Open_Price']

                try:
                    if (signal['Signal'] == 'BUY' and
                            symbol not in current_positions and
                            len(current_positions) < max_positions):

                        risk_amount = capital * (risk_pct / 100)
                        stop_distance = open_price * 0.02
                        shares_by_risk = int(risk_amount / stop_distance)

                        max_position_value = capital * (max_position_pct / 100)
                        max_shares_by_value = int(max_position_value / open_price)

                        position_size = min(shares_by_risk, max_shares_by_value)
                        position_size = max(1, position_size)

                        current_positions[symbol] = {
                            'price': open_price,
                            'size': position_size,
                            'value': position_size * open_price,
                            'entry_date': date
                        }

                        all_trades.append({
                            'Symbol': symbol,
                            'Date': date.strftime('%Y-%m-%d'),
                            'Signal': 'BUY',
                            'Price': round(open_price, 2),
                            'Shares': position_size,
                            'Value': round(position_size * open_price, 0),
                            'Positions': len(current_positions)
                        })

                    elif (signal['Signal'] == 'SELL' and symbol in current_positions):
                        exit_price = open_price
                        pos = current_positions.pop(symbol)

                        holding_days = (date - pos['entry_date']).days
                        pnl = pos['size'] * (exit_price - pos['price'])
                        capital += pnl

                        all_trades.append({
                            'Symbol': symbol,
                            'Date': date.strftime('%Y-%m-%d'),
                            'Signal': 'SELL',
                            'Price': round(exit_price, 2),
                            'Shares': int(pos['size']),
                            'PnL': round(pnl, 2),
                            'Total Capital': round(capital, 2),
                            'Holding Days': holding_days
                        })

                except Exception:
                    continue

            # STEP 4: Calculate metrics
            sell_trades = [t for t in all_trades if t.get('Signal') == 'SELL']
            years = (end_date - start_date).days / 365.25
            cagr = ((capital / initial_capital) ** (1 / years) - 1) * 100 if years > 0 and sell_trades else 0

            st.session_state.backtest_data = {
                'trades': all_trades,
                'final_capital': float(capital),
                'cagr': float(cagr),
                'total_trades': len(sell_trades),
                'symbols_processed': successful_symbols,
                'avg_holding_days': np.mean([t.get('Holding Days', 0) for t in sell_trades]) if sell_trades else 0
            }
            st.session_state.page = 1

        st.success(f"✅ Backtest complete! Processed {successful_symbols}/{len(symbols)} symbols.")
        st.rerun()

    if st.session_state.backtest_data is not None:
        backtest_data = st.session_state.backtest_data
        trades_df = pd.DataFrame(backtest_data['trades'])

        if not trades_df.empty:
            final_capital = float(backtest_data['final_capital'])
            cagr_val = float(backtest_data['cagr'])
            total_trades = int(backtest_data['total_trades'])
            avg_holding_days = round(backtest_data.get('avg_holding_days', 0), 1)

            col1_, col2_, col3_, col4_, col5_ = st.columns(5)
            with col1_:
                st.metric("Final Capital", f"₹{final_capital:,.0f}")
            with col2_:
                st.metric("CAGR", f"{cagr_val:.1f}%")
            with col3_:
                st.metric("Total Trades", f"{total_trades}")
            with col4_:
                profitable = len([t for t in backtest_data['trades'] if t.get('PnL', 0) > 0])
                win_rate = profitable / total_trades * 100 if total_trades > 0 else 0
                st.metric("Win Rate", f"{win_rate:.1f}%")
            with col5_:
                st.metric("Avg Holding", f"{avg_holding_days:.0f} days")

            st.info("""
            **📊 Position Sizing & Holding Logic:**
            - Risk per trade: **1%** of capital
            - Max position: **10%** of capital per stock
            - **Holding Days**: Calendar days from BUY to SELL signal
            - **Shares = min(risk-based, max-value shares)**
            """)

            st.subheader("📋 Complete Trade Log")
            trades_per_page = st.select_slider("Trades per page", options=[25, 50, 100, 250], value=50)
            total_pages = (len(trades_df) + trades_per_page - 1) // trades_per_page

            col_page, col_info = st.columns([1, 3])
            with col_page:
                page = st.number_input("Page", min_value=1, max_value=total_pages,
                                       value=st.session_state.page, key='page_input')
            with col_info:
                st.info(f"**Page {page} of {total_pages}** | {len(trades_df)} total trades")

            start_idx = (page - 1) * trades_per_page
            end_idx = min(start_idx + trades_per_page, len(trades_df))
            page_trades = trades_df.iloc[start_idx:end_idx].copy()

            for col in ['Price', 'PnL', 'Total Capital', 'Value', 'Holding Days']:
                if col in page_trades.columns:
                    page_trades[col] = pd.to_numeric(page_trades[col], errors='coerce').round(2)
                    if col == 'Holding Days':
                        page_trades[col] = page_trades[col].apply(lambda x: f"**{x}**" if pd.notna(x) else "")

            st.dataframe(page_trades, use_container_width=True, height=400)

            c1, c2, c3 = st.columns([1, 2, 1])
            with c1:
                if st.button("⬅️ Previous", disabled=page == 1, key='prev'):
                    st.session_state.page = page - 1
                    st.rerun()
            with c2:
                st.write(f"**{page} / {total_pages}**")
            with c3:
                if st.button("➡️ Next", disabled=page == total_pages, key='next'):
                    st.session_state.page = page + 1
                    st.rerun()

            csv = trades_df.to_csv(index=False)
            st.download_button(
                label="📥 Download All Trades CSV",
                data=csv,
                file_name="knoxville_trades.csv",
                mime="text/csv"
            )
        else:
            st.warning("No trades generated. Try adjusting parameters or date range.")

        if st.button("🔄 New Backtest", type="secondary"):
            for key in ['backtest_data', 'page']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

st.markdown("---")
st.caption("🎯 **Trading App**")
