import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="SMC Coder Pro", layout="wide", page_icon="🎯")

class EnhancedICTBot:
    def __init__(self, symbol: str, timeframes=None, lookback: int = 100):
        self.symbol = symbol
        self.timeframes = timeframes or ['15m']
        self.lookback = lookback
        self.data = {}
        self.levels = {'bullish_fvg': [], 'bearish_fvg': [], 'bos': [], 'choch': []}
        self.liquidity = {'bsl': 0, 'ssl': 0}
        self.signals = {'buy_time': [], 'buy_price': []}

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
            st.error(f"Data Error: {e}")
            return False

    def detect_fvg_and_signals(self, tf='15m'):
        df = self.data.get(tf)
        if df is None: return
        self.levels['bullish_fvg'] = []
        for i in range(2, len(df)):
            atr = df['ATR'].iloc[i]
            if df['Low'].iloc[i] > df['High'].iloc[i-2]:
                gap = df['Low'].iloc[i] - df['High'].iloc[i-2]
                if gap > (atr * 0.1):
                    self.levels['bullish_fvg'].append({'top': df['Low'].iloc[i], 'bottom': df['High'].iloc[i-2], 'time': df.index[i]})
        
        self.signals = {'buy_time': [], 'buy_price': []}
        for i in range(10, len(df)):
            for fvg in self.levels['bullish_fvg'][-5:]:
                if fvg['time'] < df.index[i] and df['Low'].iloc[i] <= fvg['top'] and df['Close'].iloc[i] > fvg['bottom']:
                    if df.index[i] not in self.signals['buy_time']:
                        self.signals['buy_time'].append(df.index[i])
                        self.signals['buy_price'].append(df['Low'].iloc[i] - (df['ATR'].iloc[i] * 0.3))

    def detect_liquidity(self, tf='15m'):
        df = self.data.get(tf)
        if df is None: return
        recent_df = df.tail(50)
        self.liquidity['bsl'] = recent_df['High'].max()
        self.liquidity['ssl'] = recent_df['Low'].min()

    def plot_dashboard(self, tf='15m'):
        df = self.data.get(tf)
        if df is None: return
        df = df.tail(100)
        
        fig = go.Figure(data=[go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], 
            increasing_line_color='#26a69a', decreasing_line_color='#ef5350',
            increasing_fillcolor='#26a69a', decreasing_fillcolor='#ef5350'
        )])

        for fvg in self.levels['bullish_fvg'][-3:]:
            start_time = fvg['time'] if fvg['time'] >= df.index[0] else df.index[0]
            fig.add_shape(type="rect", x0=start_time, x1=df.index[-1], y0=fvg['bottom'], y1=fvg['top'],
                          fillcolor="rgba(38, 166, 154, 0.15)", line=dict(color="rgba(38, 166, 154, 0.5)", width=1))

        fig.add_hline(y=self.liquidity['bsl'], line_dash="dash", line_color="#ff9800", opacity=0.6)
        fig.add_hline(y=self.liquidity['ssl'], line_dash="dash", line_color="#ff9800", opacity=0.6)

        if self.signals['buy_time']:
            v_times = [t for t in self.signals['buy_time'] if t >= df.index[0]]
            v_prices = [p for t, p in zip(self.signals['buy_time'], self.signals['buy_price']) if t >= df.index[0]]
            fig.add_trace(go.Scatter(x=v_times, y=v_prices, mode='markers', # 'mode' se text hata diya
                                     marker=dict(symbol='triangle-up', size=12, color='#00E676'),
                                     name='Buy Signal'))

        fig.update_layout(
            template="plotly_dark", plot_bgcolor="#131722", paper_bgcolor="#131722",
            xaxis_rangeslider_visible=False,
            height=700, margin=dict(l=10, r=10, b=10, t=10),
            dragmode='pan', # Ek ungli se move karne ke liye
            xaxis=dict(fixedrange=False, showgrid=False), # Zoom enable karne ke liye
            yaxis=dict(fixedrange=False, showgrid=True, gridcolor="#363c4e", side='right') # Zoom enable
        )
        
        # Config mein 'scrollZoom': True hona zaroori hai
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

# --- UI ---
st.title("🎯 The SMC Sniper Pro")
c1, c2, c3 = st.columns([2, 1, 1])
with c1: sym = st.text_input("Symbol:", value="BTC-USD")
with c2: tf = st.selectbox("TF:", options=['1m', '5m', '15m', '1h'], index=2)
with c3: 
    st.write("###")
    btn = st.button("Hunt 🎯", type="primary")

if btn:
    bot = EnhancedICTBot(symbol=sym, timeframes=[tf])
    if bot.fetch_all_data():
        bot.detect_fvg_and_signals(tf=tf)
        bot.detect_liquidity(tf=tf)
        bot.plot_dashboard(tf=tf)
