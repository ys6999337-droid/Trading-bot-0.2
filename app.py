import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import requests
import warnings

warnings.filterwarnings('ignore')

# --- STREAMLIT PAGE SETUP ---
st.set_page_config(page_title="SMC Coder Dashboard", layout="wide", page_icon="🤖")

# --- MAIN BOT CLASS ---
class EnhancedICTBot:
    def __init__(self, symbol: str, timeframes=None, lookback: int = 100):
        self.symbol = symbol
        self.timeframes = timeframes or ['15m', '1h', '1d']
        self.lookback = lookback
        self.data = {}
        self.levels = {'bullish_fvg': [], 'bearish_fvg': [], 'bos': [], 'choch': []}

    def fetch_all_data(self) -> bool:
        try:
            for tf in self.timeframes:
                ticker = yf.Ticker(self.symbol)
                period = f"{self.lookback}d"
                if tf in ['15m', '5m', '1m'] and self.lookback > 59: 
                    period = "59d"
                
                df = ticker.history(period=period, interval=tf)
                if not df.empty:
                    df['TR'] = np.maximum(
                        df['High'] - df['Low'], 
                        np.maximum(
                            abs(df['High'] - df['Close'].shift(1)), 
                            abs(df['Low'] - df['Close'].shift(1))
                        )
                    )
                    df['ATR'] = df['TR'].rolling(window=14).mean()
                    self.data[tf] = df
            return True
        except Exception as e:
            st.error(f"Data Fetch Error: {e}")
            return False

    def detect_structure(self, tf='1h', window=5):
        df = self.data.get(tf)
        if df is None: return

        for i in range(window, len(df) - 1):
            is_high = df['High'].iloc[i] == df['High'].iloc[i-window:i+window].max()
            is_low = df['Low'].iloc[i] == df['Low'].iloc[i-window:i+window].min()

            if df['Close'].iloc[-1] > df['High'].iloc[i] and is_high:
                self.levels['bos'].append({'level': df['High'].iloc[i]})
            
            if df['Close'].iloc[-1] < df['Low'].iloc[i] and is_high:
                self.levels['choch'].append({'level': df['Low'].iloc[i]})

    def detect_fvg(self, tf='1h'):
        df = self.data.get(tf)
        if df is None: return
        
        for i in range(2, len(df)):
            atr = df['ATR'].iloc[i]
            if df['Low'].iloc[i] > df['High'].iloc[i-2]:
                gap = df['Low'].iloc[i] - df['High'].iloc[i-2]
                if gap > (atr * 0.2):
                    self.levels['bullish_fvg'].append({
                        'top': df['Low'].iloc[i], 
                        'bottom': df['High'].iloc[i-2],
                        'time': df.index[i]  # <-- Yahan time add kiya taaki pata chale box kahan se draw karna hai
                    })

    # STREAMLIT CHART PLOTTING
    def plot_dashboard(self, tf='1h'):
        df = self.data.get(tf)
        if df is None: return
        df = df.tail(100) 
        
        fig = go.Figure(data=[go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], 
            low=df['Low'], close=df['Close'], name='Price'
        )])

        for fvg in self.levels['bullish_fvg'][-5:]:
            # Box wahi se shuru hoga jahan FVG bana tha
            start_time = fvg['time'] if fvg['time'] >= df.index[0] else df.index[0]

            fig.add_shape(
                type="rect", 
                x0=start_time, x1=df.index[-1], 
                y0=fvg['bottom'], y1=fvg['top'],
                fillcolor="rgba(0, 255, 0, 0.2)", 
                line=dict(color="rgba(0, 255, 0, 0.7)", width=1) # Box par border add kiya clean look ke liye
            )

        fig.update_layout(
            title=f"{self.symbol} - SMC Custom Dashboard", 
            template="plotly_dark", 
            xaxis_rangeslider_visible=False,
            height=600
        )
        st.plotly_chart(fig, use_container_width=True)


# --- STREAMLIT UI UPDATE ---
st.title("🤖 The SMC Coder - Live Dashboard")

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    user_symbol = st.text_input("Enter Asset Symbol (e.g. BTC-USD, ^NSEI):", value="EURUSD=X")

with col2:
    # Yahan se aap timeframe select kar sakte hain
    selected_tf = st.selectbox("Select Timeframe:", options=['1m', '5m', '15m', '1h', '1d'], index=2)

with col3:
    st.write("###") # Thoda gap dene ke liye
    run_btn = st.button("Run Live Analysis", type="primary")

if run_btn:
    with st.spinner(f"Fetching {selected_tf} data..."):
        # Humne 'selected_tf' ko bot mein pass kiya
        bot = EnhancedICTBot(symbol=user_symbol, lookback=50, timeframes=[selected_tf])
        
        if bot.fetch_all_data():
            bot.detect_structure(tf=selected_tf)
            bot.detect_fvg(tf=selected_tf)
            
            st.success(f"Analysis Done for {selected_tf} timeframe!")
            
            # Stats
            s1, s2 = st.columns(2)
            s1.metric("Bullish FVGs Found", len(bot.levels['bullish_fvg']))
            s2.metric("Structure Breaks", len(bot.levels['bos']))
            
            # Chart
            bot.plot_dashboard(tf=selected_tf)

