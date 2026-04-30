import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import warnings

warnings.filterwarnings('ignore')

# --- STREAMLIT PAGE SETUP ---
st.set_page_config(page_title="SMC Coder Dashboard", layout="wide", page_icon="🎯")

class EnhancedICTBot:
    def __init__(self, symbol: str, timeframes=None, lookback: int = 100):
        self.symbol = symbol
        self.timeframes = timeframes or ['15m']
        self.lookback = lookback
        self.data = {}
        self.levels = {'bullish_fvg': [], 'bearish_fvg': [], 'bos': [], 'choch': []}
        self.liquidity = {'bsl': 0, 'ssl': 0}
        self.signals = {'buy_time': [], 'buy_price': [], 'sell_time': [], 'sell_price': []}

    def fetch_all_data(self) -> bool:
        try:
            for tf in self.timeframes:
                ticker = yf.Ticker(self.symbol)
                period = "59d" if tf in ['1m', '5m', '15m'] else f"{self.lookback}d"
                df = ticker.history(period=period, interval=tf)
                if not df.empty:
                    df['TR'] = np.maximum(df['High'] - df['Low'], np.maximum(abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))))
                    df['ATR'] = df['TR'].rolling(window=14).mean()
                    self.data[tf] = df
            return True
        except Exception as e:
            st.error(f"Data Fetch Error: {e}")
            return False

    def detect_fvg_and_signals(self, tf='15m'):
        df = self.data.get(tf)
        if df is None: return
        
        # Detect FVG
        for i in range(2, len(df)):
            atr = df['ATR'].iloc[i]
            # Bullish FVG
            if df['Low'].iloc[i] > df['High'].iloc[i-2]:
                gap = df['Low'].iloc[i] - df['High'].iloc[i-2]
                if gap > (atr * 0.1):
                    self.levels['bullish_fvg'].append({
                        'top': df['Low'].iloc[i], 
                        'bottom': df['High'].iloc[i-2],
                        'time': df.index[i]
                    })
                    
        # Detect Signals (Simple FVG Mitigation Logic)
        for i in range(10, len(df)):
            current_low = df['Low'].iloc[i]
            current_close = df['Close'].iloc[i]
            
            # Agar FVG tap hua aur price upar close hui -> BUY
            for fvg in self.levels['bullish_fvg'][-5:]:
                if fvg['time'] < df.index[i] and current_low <= fvg['top'] and current_close > fvg['bottom']:
                    if df.index[i] not in self.signals['buy_time']:
                        self.signals['buy_time'].append(df.index[i])
                        self.signals['buy_price'].append(df['Low'].iloc[i] - (df['ATR'].iloc[i] * 0.2)) # Arrow thoda niche banega

    def detect_liquidity(self, tf='15m'):
        df = self.data.get(tf)
        if df is None: return
        
        # Last 50 candles ki liquidity
        recent_df = df.tail(50)
        self.liquidity['bsl'] = recent_df['High'].max()
        self.liquidity['ssl'] = recent_df['Low'].min()

    # --- TRADINGVIEW STYLE CHART ---
    def plot_dashboard(self, tf='15m'):
        df = self.data.get(tf)
        if df is None: return
        df = df.tail(100) # Chart clean rakhne ke liye 100 candles
        
        # 1. TradingView style Candles
        fig = go.Figure(data=[go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], 
            name='Price',
            increasing_line_color='#26a69a', decreasing_line_color='#ef5350', # TV Colors
            increasing_fillcolor='#26a69a', decreasing_fillcolor='#ef5350'
        )])

        # 2. Bullish FVG Zones with Names
        for fvg in self.levels['bullish_fvg'][-3:]: # Sirf fresh 3 FVGs
            start_time = fvg['time'] if fvg['time'] >= df.index[0] else df.index[0]
            
            # Zone Box
            fig.add_shape(
                type="rect", x0=start_time, x1=df.index[-1], y0=fvg['bottom'], y1=fvg['top'],
                fillcolor="rgba(38, 166, 154, 0.15)", line=dict(color="rgba(38, 166, 154, 0.5)", width=1)
            )
            # Zone Text
            fig.add_annotation(
                x=start_time, y=fvg['top'], text="Bullish FVG", 
                showarrow=False, xanchor='left', yanchor='bottom',
                font=dict(color="#26a69a", size=10)
            )

        # 3. Liquidity Lines (BSL & SSL)
        if self.liquidity['bsl'] > 0:
            # BSL Line (Upper)
            fig.add_hline(y=self.liquidity['bsl'], line_dash="dash", line_color="#ff9800", opacity=0.7)
            fig.add_annotation(x=df.index[-10], y=self.liquidity['bsl'], text="BSL (Liquidity)", showarrow=False, yanchor='bottom', font=dict(color="#ff9800"))
            
            # SSL Line (Lower)
            fig.add_hline(y=self.liquidity['ssl'], line_dash="dash", line_color="#ff9800", opacity=0.7)
            fig.add_annotation(x=df.index[-10], y=self.liquidity['ssl'], text="SSL (Liquidity)", showarrow=False, yanchor='top', font=dict(color="#ff9800"))

        # 4. BUY Signals (Green Arrows)
        if self.signals['buy_time']:
            valid_times = [t for t in self.signals['buy_time'] if t >= df.index[0]]
            valid_prices = [p for t, p in zip(self.signals['buy_time'], self.signals['buy_price']) if t >= df.index[0]]
            
            fig.add_trace(go.Scatter(
                x=valid_times, y=valid_prices, mode='markers+text', 
                marker=dict(symbol='triangle-up', size=15, color='#00E676'),
                text="BUY", textposition="bottom center", textfont=dict(color="#00E676", size=12),
                name='Buy Signal'
            ))

        # TradingView Dark Theme Background
        fig.update_layout(
            title=f"Live Asset: {self.symbol}", 
            template="plotly_dark", 
            plot_bgcolor="#131722", paper_bgcolor="#131722", # TV Dark background
            xaxis_rangeslider_visible=False,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#363c4e", side='right'), # TV y-axis right mein hota hai
            height=650, margin=dict(l=10, r=10, b=10, t=40),
            dragmode='pan'  # <--- FIX 1: Isse chart drag karne par TV ki tarah move hoga
        )
        
        # <--- FIX 2: config={'scrollZoom': True} se pinch-to-zoom aur mouse wheel zoom on ho jayega
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})


# --- STREAMLIT UI ---
st.title("🎯 The SMC Sniper - Pro Dashboard")

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    user_symbol = st.text_input("Asset Symbol (e.g. BTC-USD, GC=F):", value="EURUSD=X")
with col2:
    selected_tf = st.selectbox("Timeframe:", options=['1m', '5m', '15m', '1h'], index=2)
with col3:
    st.write("###")
    run_btn = st.button("Hunt Liquidity 🎯", type="primary")

if run_btn:
    with st.spinner(f"Scanning market structure for {selected_tf}..."):
        bot = EnhancedICTBot(symbol=user_symbol, lookback=50, timeframes=[selected_tf])
        
        if bot.fetch_all_data():
            bot.detect_fvg_and_signals(tf=selected_tf)
            bot.detect_liquidity(tf=selected_tf)
            
            bot.plot_dashboard(tf=selected_tf)
