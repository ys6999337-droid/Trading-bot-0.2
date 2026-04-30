import pandas as pd
import numpy as np
import yfinance as yf
import logging
import plotly.graph_objects as go
import requests
from datetime import datetime, time
from typing import List, Dict, Optional
from enum import Enum
import warnings

# --- SETUP & LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')

class TradeDirection(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"

# --- MAIN BOT CLASS ---
class EnhancedICTBot:
    def __init__(self, symbol: str, timeframes: List[str] = None, lookback: int = 100):
        self.symbol = symbol
        self.timeframes = timeframes or ['15m', '1h', '1d']
        self.lookback = lookback
        self.data = {}
        self.levels = {'bullish_fvg': [], 'bearish_fvg': [], 'demand_zones': [], 'supply_zones': [], 'bos': [], 'choch': []}
        logger.info(f"🤖 The SMC Coder Bot Initialized for {symbol}")

    # --- 1. DATA FETCHING & INDICATORS ---
    def fetch_all_data(self) -> bool:
        try:
            for tf in self.timeframes:
                ticker = yf.Ticker(self.symbol)
                
                # Fixing YFinance Intraday Period Limits
                period = f"{self.lookback}d"
                if tf in ['15m', '5m', '1m'] and self.lookback > 59: 
                    period = "59d"
                
                df = ticker.history(period=period, interval=tf)
                if not df.empty:
                    # Calculate ATR for dynamic filtering
                    df['TR'] = np.maximum(
                        df['High'] - df['Low'], 
                        np.maximum(
                            abs(df['High'] - df['Close'].shift(1)), 
                            abs(df['Low'] - df['Close'].shift(1))
                        )
                    )
                    df['ATR'] = df['TR'].rolling(window=14).mean()
                    self.data[tf] = df
                    logger.info(f"✅ Data fetched for {tf}")
            return True
        except Exception as e:
            logger.error(f"Data Fetch Error: {e}")
            return False

    # --- 2. MARKET STRUCTURE (BOS & CHoCH) ---
    def detect_structure(self, tf='1h', window=5):
        df = self.data.get(tf)
        if df is None: return

        for i in range(window, len(df) - 1):
            is_high = df['High'].iloc[i] == df['High'].iloc[i-window:i+window].max()
            is_low = df['Low'].iloc[i] == df['Low'].iloc[i-window:i+window].min()

            # BOS (Break of Structure)
            if df['Close'].iloc[-1] > df['High'].iloc[i] and is_high:
                self.levels['bos'].append({'time': df.index[i], 'level': df['High'].iloc[i], 'type': 'Bullish BOS'})
            
            # CHoCH (Change of Character)
            if df['Close'].iloc[-1] < df['Low'].iloc[i] and is_high:
                self.levels['choch'].append({'time': df.index[i], 'level': df['Low'].iloc[i], 'type': 'Bearish CHoCH'})

    # --- 3. FAIR VALUE GAPS (ATR FILTERED) ---
    def detect_fvg(self, tf='1h'):
        df = self.data.get(tf)
        if df is None: return
        
        for i in range(2, len(df)):
            atr = df['ATR'].iloc[i]
            # Bullish FVG
            if df['Low'].iloc[i] > df['High'].iloc[i-2]:
                gap = df['Low'].iloc[i] - df['High'].iloc[i-2]
                if gap > (atr * 0.2): # Minimum gap filter
                    self.levels['bullish_fvg'].append({
                        'top': df['Low'].iloc[i], 
                        'bottom': df['High'].iloc[i-2], 
                        'time': df.index[i]
                    })

    # --- 4. DISCORD WEBHOOK ALERTS ---
    def send_discord_alert(self, title: str, description: str, color: int = 0x00FF00):
        # Yahan apna Discord Webhook URL paste karein
        webhook_url = "YOUR_DISCORD_WEBHOOK_URL_HERE" 
        
        if webhook_url == "YOUR_DISCORD_WEBHOOK_URL_HERE":
            logger.warning("⚠️ Discord webhook URL add nahi kiya gaya hai. Alert skip ho raha hai.")
            return

        data = {
            "username": "The SMC Coder Bot",
            "embeds": [
                {
                    "title": title,
                    "description": description,
                    "color": color,
                    "footer": {"text": "Developed by The SMC Coder 🤖"}
                }
            ]
        }
        
        try:
            response = requests.post(webhook_url, json=data)
            if response.status_code == 204:
                logger.info(f"🔔 Discord Alert Sent: {title}")
            else:
                logger.error(f"Discord Alert Failed: Code {response.status_code}")
        except Exception as e:
            logger.error(f"Discord Webhook Error: {e}")

    # --- 5. INTERACTIVE DASHBOARD (PLOTLY) ---
    def plot_dashboard(self, tf='1h'):
        df = self.data.get(tf).tail(100) # Last 100 candles for clean view
        fig = go.Figure(data=[go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], 
            low=df['Low'], close=df['Close'], name='Price'
        )])

        # Draw Bullish FVGs on Chart
        for fvg in self.levels['bullish_fvg'][-5:]: # Highlight last 5 FVGs
            fig.add_shape(
                type="rect", x0=df.index[0], x1=df.index[-1], 
                y0=fvg['bottom'], y1=fvg['top'],
                fillcolor="rgba(0, 255, 0, 0.2)", line_width=0
            )

        fig.update_layout(
            title=f"{self.symbol} - SMC Custom Dashboard", 
            template="plotly_dark", 
            xaxis_rangeslider_visible=False
        )
        fig.show()

    # --- 6. RUN MASTER ANALYSIS ---
    def run_analysis(self):
        logger.info(f"🔍 Starting Analysis for {self.symbol}...")
        
        if self.fetch_all_data():
            self.detect_structure()
            self.detect_fvg()
            logger.info("✅ Core Analysis Complete.")
            
            # Prepare & Send Alert
            total_fvg = len(self.levels['bullish_fvg'])
            total_bos = len(self.levels['bos'])
            
            alert_msg = f"**Symbol:** {self.symbol}\n"
            alert_msg += f"**Bullish FVGs Found:** {total_fvg}\n"
            alert_msg += f"**Structure Breaks (BOS):** {total_bos}\n"
            alert_msg += "Open your custom dashboard to check liquidity zones! 🎯"
            
            self.send_discord_alert(
                title="🚨 High Probability Setup Detected!", 
                description=alert_msg, 
                color=0x00FF00
            )
            
            # Show Chart
            self.plot_dashboard()

# --- EXECUTION ---
if __name__ == "__main__":
    # Aap is symbol ko Gold (GC=F) ya kisi Nifty stock mein badal sakte hain
    bot = EnhancedICTBot(symbol='EURUSD=X', lookback=50)
    bot.run_analysis()
