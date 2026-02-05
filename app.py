import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import pytz
from datetime import datetime
import numpy as np
import requests

# 嘗試匯入 twstock，如果沒有安裝則提示
try:
    import twstock
except ImportError:
    st.error("⚠️ 請安裝 twstock 套件： pip install twstock")
    st.stop()

# === 1. 系統初始化 ===
st.set_page_config(page_title="遠東集團 & Global Peers 戰情室", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

# CSS 美化
st.markdown("""
    <style>
        html, body, [class*="css"]  { font-family: 'Microsoft JhengHei', -apple-system, BlinkMacSystemFont, sans-serif !important; }
        .stApp { background-color: #f9f9f9; }
        .main-title {
            font-size: 2.5rem !important;
            font-weight: 600;
            color: #1d1d1f;
            text-align: center;
            margin-top: 1rem;
            margin-bottom: 2rem;
            letter-spacing: 0.5px;
        }
        div[data-testid="stVerticalBlock"] > div[class*="css-1d391kg"] {
            background: white;
            border-radius: 18px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            padding: 2rem;
            margin-bottom: 2rem;
        }
        div[data-testid="stMetricValue"] { font-size: 2.2rem !important; font-weight: 700; color: #1d1d1f; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">遠東集團 & Global Peers<br>聯合稽核戰情室</div>', unsafe_allow_html=True)

# === 2. 核心引擎：資料取得 ===

# (A) 台股專用引擎 (使用 twstock 直連證交所)
def get_tw_realtime(stock_code):
    try:
        # 去除 .TW 後綴 (例如 1402.TW -> 1402)
        code = stock_code.split('.')[0]
        
        # 呼叫 twstock 抓取即時資料
        stock = twstock.realtime.get(code)
        
        if not stock['success']:
            return None
            
        rt = stock['realtime']
        info = stock['info']
        
        # 處理資料型態 (API 回傳多為字串，需轉 float)
        # 注意：若剛開盤或沒成交，可能是 '-'，需容錯處理
        def safe_float(val):
            try:
                return float(val)
            except:
                return 0.0

        current = safe_float(rt['latest_trade_price'])
        open_p = safe_float(rt['open'])
        high = safe_float(rt['high'])
        low = safe_float(rt['low'])
        
        # 昨收在 info 裡面，欄位不一定叫 previous_close，有時需計算
        # twstock 沒直接給昨收，通常用 (最新價 - 漲跌) 反推，或抓 info
        # 這裡簡單用 'best_bid_price' 當作參考或從 yfinance 補
        # 為了準確，我們還是簡單用 yfinance 補昨收，或者忽略昨收的精確計算
        # 這裡用一個簡單 hack: 證交所資料有 "差價"，但我們要昨收
        # 昨收 = 現價 - (漲跌價差) ? 不一定準
        # 暫時用 yfinance 補昨收和 K 線，但價格用 twstock
        return {
            "current": current,
            "open": open_p,
            "high": high,
            "low": low,
            "volume": int(safe_float(rt['accumulate_trade_volume'])),
            "source": "TWSE (證交所)"
        }
    except Exception as e:
        print(f"Twstock error: {e}")
        return None

# (B) 通用引擎 (使用 yfinance，含偽裝)
@st.cache_data(ttl=60)
def get_yfinance_data(symbol):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        session = requests.Session()
        session.headers.update(headers)
        ticker = yf.Ticker(symbol, session=session)
        
        # 抓 K 線圖 (包含昨收)
        df = ticker.history(period="1d", interval="5m")
        if df.empty:
            df = ticker.history(period="5d", interval="60m")
            if not df.empty:
                df = df[df.index.date == df.index[-1].date()]

        info = ticker.info
        prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
        current = info.get('currentPrice')
        
        # 補救數據
        if prev_close is None and not df.empty:
             prev_close = df['Open'].iloc[0]
        if current is None and not df.empty:
            current = df['Close'].iloc[-1]
            
        currency = info.get('currency', 'TWD')

        return {
            "df": df,
            "current": current,
            "prev_close": prev_close,
            "volume": df['Volume'].sum() if not df.empty else 0,
            "vwap": (df['Close'].mean()) if not df.empty else 0, # 簡化計算
            "currency": currency,
            "source": "Yahoo Finance"
        }
    except:
        return None

# === 3. 整合資料邏輯 ===
def get_hybrid_data(symbol, is_tw_stock=False):
    # 1. 先抓 yfinance (因為需要 K 線圖和昨收)
    yf_data = get_yfinance_data(symbol)
    
    # 2. 如果是台股，啟動「雙引擎修正」
    if is_tw_stock:
        # 呼叫 twstock
        tw_data = get_tw_realtime(symbol)
        
        if tw_data and tw_data['current'] > 0:
            # ✅ 成功！使用證交所的超準價格覆蓋 Yahoo 的舊價格
            final_current = tw_data['current']
            final_open = tw_data['open']
            final_high = tw_data['high']
            final_low = tw_data['low']
            final_vol = tw_data['volume']
            source = "🚀 TWSE (證交所即時)"
        else:
            # ❌ 證交所沒回傳 (可能收盤或擋IP)，退回使用 Yahoo
            if yf_data:
                final_current = yf_data['current']
                final_open = yf_data['df']['Open'].iloc[0] if not yf_data['df'].empty else 0
                final_high = yf_data['df']['High'].max() if not yf_data['df'].empty else 0
                final_low = yf_data['df']['Low'].min() if not yf_data['df'].empty else 0
                final_vol = yf_data['volume']
                source = "Yahoo (備援)"
            else:
                return None
    else:
        # 美股，只能用 Yahoo
        if not yf_data: return None
        final_current = yf_data['current']
        # 美股 Intraday 可能沒 Open/High/Low，從 df 抓
        if not yf_data['df'].empty:
            final_open = yf_data['df']['Open'].iloc[0]
            final_high = yf_data['df']['High'].max()
            final_low = yf_data['df']['Low'].min()
        else:
            final_open = final_current
            final_high = final_current
            final_low = final_current
        final_vol = yf_data['volume']
        source = "Yahoo Finance"

    # 整合回傳
    return {
        "current": final_current,
        "open": final_open,
        "high": final_high,
        "low": final_low,
        "volume": final_vol,
        "prev_close": yf_data['prev_close'] if yf_data else final_open, # 昨收仍依賴 Yahoo
        "df": yf_data['df'] if yf_data else pd.DataFrame(),
        "currency": yf_data['currency'] if yf_data else ("TWD" if is_tw_stock else "USD"),
        "source": source
    }

# === 4. 繪圖與 UI ===
def make_chart(df, prev_close, currency):
    if df.empty: return None
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
    
    # K線
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name="Price", increasing_line_color='#d62728', decreasing_line_color='#2ca02c'
    ), row=1, col=1)
    
    # 昨收
    if prev_close:
        fig.add_hline(y=prev_close, line_dash="dash", line_color="gray", row=1, col=1)
    
    # 成交量
    colors = ['#d62728' if r['Close'] >= r['Open'] else '#2ca02c' for _, r in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name="Vol"), row=2, col=1)
    
    fig.update_layout(height=500, xaxis_rangeslider_visible=False, showlegend=False, 
                     margin=dict(t=20, b=20, l=40, r=40), yaxis=dict(title=currency))
    return fig

# === 5. 側邊欄與執行 ===
stock_categories = {
    "🇹🇼 遠東集團 (TW)": {
        "1402 遠東新": "1402.TW", "1102 亞泥": "1102.TW", "2845 遠銀": "2845.TW",
        "2606 裕民": "2606.TW", "1460 宏遠": "1460.TW", "2903 遠百": "2903.TW",
        "4904 遠傳": "4904.TW", "1710 東聯": "1710.TW"
    },
    "🇺🇸 國際品牌 (US)": {
        "Nike": "NKE", "Under Armour": "UAA", "Adidas (ADR)": "ADDYY",
        "Lululemon": "LULU", "Coca-Cola": "KO", "Pepsi": "PEP"
    }
}

category = st.sidebar.selectbox("選擇市場", list(stock_categories.keys()))
stock_map = stock_categories[category]
name = st.sidebar.radio("公司", list(stock_map.keys()))
symbol = stock_map[name]

if st.sidebar.button("🔄 更新"): st.cache_data.clear()

# 判斷是否為台股 (決定要不要開 twstock 引擎)
is_tw = "TW" in category
data = get_hybrid_data(symbol, is_tw_stock=is_tw)

# 顯示介面
col_l, col_r = st.columns([3, 1])
with col_l:
    st.title(f"{name}")
    if data:
        curr = data['current']
        prev = data['prev_close']
        chg = curr - prev if prev else 0
        pct = (chg/prev)*100 if prev else 0
        
        st.markdown(f"###### 資料來源: **{data['source']}**") # 讓你知道現在是誰在工作
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("現價", f"{curr:.2f}", f"{chg:+.2f} ({pct:+.2f}%)", delta_color="inverse")
        m2.metric("開盤", f"{data['open']:.2f}")
        m3.metric("最高", f"{data['high']:.2f}")
        m4.metric("最低", f"{data['low']:.2f}")
        
        if not data['df'].empty:
            st.plotly_chart(make_chart(data['df'], prev, data['currency']), use_container_width=True)
        else:
            st.warning("⚠️ 即時報價正常 (twstock)，但 K 線圖 (Yahoo) 暫時無法讀取。")
    else:
        st.error("系統暫時無法連線，請稍後再試。")

with col_r:
    st.markdown("### 市場概況")
    # 這裡可以用同樣邏輯抓大盤
    idx_symbol = "^TWII" if is_tw else "^GSPC"
    idx_data = get_yfinance_data(idx_symbol) # 指數通常用 Yahoo 就好
    if idx_data and idx_data['current']:
        i_curr = idx_data['current']
        i_prev = idx_data['prev_close']
        i_pct = ((i_curr - i_prev)/i_prev)*100
        st.metric("大盤指數", f"{i_curr:,.0f}", f"{i_pct:+.2f}%", delta_color="inverse")
    else:
        st.info("指數讀取中...")

st.markdown("---")
st.markdown(f"<div style='text-align:center; color:#888;'>遠東集團 戰情室 | Update: {datetime.now(tw_tz).strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
