import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import pytz
from datetime import datetime
import numpy as np

# === 1. 系統初始化 ===
st.set_page_config(page_title="遠東集團_聯合稽核總部_一處戰情室", layout="wide")

# 【關鍵修正】定義台灣時區，解決 NameError
tw_tz = pytz.timezone('Asia/Taipei')

# CSS：Apple風格設計 - 極簡、優雅、大白空間、圓角、輕陰影、微軟正黑體
st.markdown("""
    <style>
        /* 全局字體：微軟正黑體 */
        html, body, [class*="css"]  { font-family: 'Microsoft JhengHei', -apple-system, BlinkMacSystemFont, sans-serif !important; }
        
        /* 主背景：純白 + 輕微質感 */
        .stApp { background-color: #f9f9f9; }
        
        /* 大標題：Apple風格，極簡大字、居中、輕盈 */
        .main-title {
            font-size: 2.8rem !important;
            font-weight: 600;
            color: #1d1d1f;
            text-align: center;
            margin-top: 2rem;
            margin-bottom: 3rem;
            letter-spacing: 0.5px;
        }
        
        /* Container：圓角 + 輕陰影（Apple卡片風） */
        div[data-testid="stVerticalBlock"] > div[class*="css-1d391kg"] {
            background: white;
            border-radius: 18px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            padding: 2rem;
            margin-bottom: 2rem;
        }
        
        /* Metric：更大更優雅 */
        div[data-testid="stMetricValue"] { font-size: 2.2rem !important; font-weight: 700; color: #1d1d1f; }
        div[data-testid="stMetricLabel"] { font-size: 1rem !important; color: #555; }
        div[data-testid="metric-container"] { padding: 0.8rem 0; }
        
        /* Sidebar：Apple風格，乾淨透明感 */
        section[data-testid="stSidebar"] {
            background-color: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border-right: 1px solid #eee;
            border-radius: 18px;
            margin: 1rem;
            padding-top: 2rem;
        }
        
        /* 圖表區間 */
        .stPlotlyChart { margin-top: 20px; border-radius: 12px; overflow: hidden; }
        
        /* 頁腳 */
        .footer { text-align: center; color: #888; font-size: 0.9rem; margin-top: 4rem; }
    </style>
""", unsafe_allow_html=True)

# 大標題
st.markdown('<div class="main-title">遠東集團<br>聯合稽核總部 一處戰情室</div>', unsafe_allow_html=True)

# === 2. 資料取得 ===
@st.cache_data(ttl=30)
def get_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # 嘗試取得昨收與現價
        prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
        current = info.get('currentPrice') or info.get('regularMarketPrice')
        
        # 取得當日 K 線數據 (優先抓 5 分鐘，若無則抓 15 分鐘)
        df = ticker.history(period="1d", interval="5m")
        if df.empty:
            df = ticker.history(period="1d", interval="15m")
        
        # 若 info 抓不到現價，改用 DataFrame 最後一筆
        if current is None and not df.empty:
            current = df['Close'].iloc[-1]
        
        volume = df['Volume'].sum() if not df.empty else 0
        
        if not df.empty:
            open_price = df['Open'].iloc[0]
            high = df['High'].max()
            low = df['Low'].min()
            # 計算 VWAP
            typical_price = (df['High'] + df['Low'] + df['Close']) / 3
            if df['Volume'].sum() > 0:
                vwap = (typical_price * df['Volume']).sum() / df['Volume'].sum()
            else:
                vwap = df['Close'].mean()
        else:
            open_price = high = low = vwap = current
        
        if current is None:
            # 若真的什麼都抓不到，回傳 None 讓外層處理
            return None
            
        return {
            "df": df,
            "current": current,
            "prev_close": prev_close or current,
            "volume": volume,
            "open": open_price,
            "high": high,
            "low": low,
            "vwap": vwap
        }
    except Exception as e:
        # 在開發階段可以 print(e) 來看錯誤，正式版則隱藏或顯示簡單訊息
        return None

# === 3. Plotly K線圖 ===
def make_candlestick_chart(df, prev_close, height=500, show_volume=True):
    if df.empty:
        return None
    
    current_price = df['Close'].iloc[-1]
    # 背景色邏輯：漲紅跌綠（淡色背景）
    bg_color = "rgba(255, 182, 193, 0
