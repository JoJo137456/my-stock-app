import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import pytz
from datetime import datetime
import numpy as np
import requests  # 新增這個，用來戴面具偽裝

# === 1. 系統初始化 ===
st.set_page_config(page_title="遠東集團 & 國際競品戰情室", layout="wide")

# 定義台灣時區
tw_tz = pytz.timezone('Asia/Taipei')

# CSS：Apple風格設計
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
        div[data-testid="stMetricLabel"] { font-size: 1rem !important; color: #555; }
        section[data-testid="stSidebar"] {
            background-color: rgba(255,255,255,0.95);
            border-right: 1px solid #eee;
        }
        .footer { text-align: center; color: #888; font-size: 0.9rem; margin-top: 4rem; }
    </style>
""", unsafe_allow_html=True)

# 大標題
st.markdown('<div class="main-title">遠東集團 & Global Peers<br>聯合稽核戰情室</div>', unsafe_allow_html=True)

# === 2. 資料取得 (已加入防擋機制) ===
@st.cache_data(ttl=30)
def get_data(symbol):
    try:
        # 1. 製作面具：設定 User-Agent，偽裝成一般的 Chrome 瀏覽器
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # 2. 建立連線 Session 並戴上面具
        session = requests.Session()
        session.headers.update(headers)

        # 3. 將這個偽裝好的 session 傳給 yfinance
        ticker = yf.Ticker(symbol, session=session)
        
        # 嘗試取得即時資訊
        try:
            info = ticker.info
            current = info.get('currentPrice') or info.get('regularMarketPrice')
            prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
        except:
            current = None
            prev_close = None
        
        # 嘗試取得 K 線圖 (優先抓 1 天 5 分鐘)
        df = ticker.history(period="1d", interval="5m")
        
        # 如果抓不到 (可能盤前或盤後)，改抓 5 天的 60 分鐘線
        if df.empty:
            df = ticker.history(period="5d", interval="60m")
            if not df.empty:
                # 只留最後一天的資料
                last_day = df.index[-1].date()
                df = df[df.index.date == last_day]

        # 補救措施：如果還是沒有當前價格，用 K 線最後一筆
        if current is None and not df.empty:
            current = df['Close'].iloc[-1]
            
        # 補救 Prev Close
        if prev_close is None and not df.empty:
            prev_close = df['Open'].iloc[0]

        # 如果真的完全抓不到，回傳 None
        if current is None:
            return None

        # 計算其他數據
        volume = df['Volume'].sum() if not df.empty else 0
        
        if not df.empty:
            open_price = df['Open'].iloc[0]
            high = df['High'].max()
            low = df['Low'].min()
            typical = (df['High'] + df['Low'] + df['Close']) / 3
            if volume > 0:
                vwap = (typical * df['Volume']).sum() / volume
            else:
                vwap = df['Close'].mean()
        else:
            open_price = high = low = vwap = current
            
        return {
            "df": df,
            "current": current,
            "prev_close": prev_close or current,
            "volume": volume,
            "open": open_price,
            "high": high,
            "low": low,
            "vwap": vwap,
            "currency": info.get('currency', 'TWD')
        }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

# === 3. Plotly K線圖 ===
def make_candlestick_chart(df, prev_close, currency, height=500, show_volume=True):
    if df.empty:
        return None
    
    current_price = df['Close'].iloc[-1]
    bg_color = "rgba(255, 182, 193, 0.15)" if current_price >= prev_close else "rgba(144, 238, 144, 0.15)"
    
    rows = 2 if show_volume else 1
    row_heights = [0.7, 0.3] if show_volume else [1.0]
    
    fig = make_subplots(
        rows=rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=row_heights
    )
    
    # K線
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='#d62728', increasing_fillcolor='#d62728',
        decreasing_line_color='#2ca02c', decreasing_fillcolor='#2ca02c',
        name="Price"
    ), row=1, col=1)
    
    # 昨收線
    fig.add_hline(y=prev_close, line_dash="dash", line_color="#888888", row=1, col=1)
    
    # 動態調整 Y 軸範圍
    y_min = df['Low'].min()
    y_max = df['High'].max()
    padding = (y_max - y_min) * 0.1 if (y_max - y_min) > 0 else y_max * 0.01
    y_range = [y_min - padding, y_max + padding]
    
    # 背景色塊 (漲跌氛圍)
    fig.add_shape(
        type="rect",
        x0=df.index[0], x1=df.index[-1],
        y0=y_range[0], y1=y_range[1],
        fillcolor=bg_color,
        line_width=0,
        layer="below",
        opacity=0.4,
        row=1, col=1
    )
    
    if show_volume:
        colors = ['#d62728' if row['Close'] >= row['Open'] else '#2ca02c' for _, row in df.iterrows()]
        fig.add_trace(go.Bar(
            x=df.index, y=df['Volume'],
            marker_color=colors,
            name="Volume"
        ), row=2, col=1)
    
    fig.update_layout(
        height=height,
        xaxis_rangeslider_visible=False,
        showlegend=False,
        plot_bgcolor='white',
        margin=dict(l=40, r=40, t=40, b=40),
        yaxis=dict(range=y_range, title=currency)
    )
    
    # 時間軸格式
    fig.update_xaxes(
        tickformat='%H:%M',
        title_text="時間" if show_volume else "",
        row=rows, col=1
    )
    
    return fig

# === 4. 主 UI 邏輯 ===

# 定義股票清單 (分類管理)
stock_categories = {
    "🇹🇼 遠東集團 (TW)": {
        "1402 遠東新": "1402.TW",
        "1102 亞泥": "1102.TW",
        "2845 遠銀": "2845.TW",
        "2606 裕民": "2606.TW",
        "1460 宏遠": "1460.TW",
        "2903 遠百": "2903.TW",
        "4904 遠傳": "4904.TW",
        "1710 東聯": "1710.TW"
    },
    "🇺🇸 國際品牌/競品 (US/ADR)": {
        "Nike (NKE)": "NKE",
        "Under Armour (UAA)": "UAA",
        "Adidas (ADDYY - ADR)": "ADDYY",
        "Puma (PUMSY - ADR)": "PUMSY",
        "Lululemon (LULU)": "LULU",
        "Columbia (COLM)": "COLM",
        "VF Corp (VFC)": "VFC",
        "Gap (GPS)": "GPS",
        "Fast Retailing (FRCOY - ADR)": "FRCOY",
        "Coca-Cola (KO)": "KO",
        "PepsiCo (PEP)": "PEP"
    }
}

st.sidebar.header("🎯 監控面板")

# 1. 選擇市場類別
category = st.sidebar.selectbox("選擇市場", list(stock_categories.keys()))

# 2. 選擇該類別下的公司
stock_map = stock_categories[category]
selected_name = st.sidebar.radio("選擇公司", list(stock_map.keys()))
ticker = stock_map[selected_name]

if st.sidebar.button("🔄 立即更新數據"):
    st.cache_data.clear()

st.sidebar.markdown("---")
st.sidebar.info(f"目前顯示幣別：{'TWD' if 'TW' in category else 'USD'}")

# 取得資料
s_data = get_data(ticker)

# 取得對比指數 (台股看加權，美股看標普500)
index_ticker = "^TWII" if "TW" in category else "^GSPC"
index_name = "🇹🇼 加權指數" if "TW" in category else "🇺🇸 S&P 500"
idx_data = get_data(index_ticker)

with st.container():
    col_main, col_index = st.columns([3.5, 1.5])
    
    with col_main:
        st.markdown(f"## 🔥 {selected_name}")
        
        if s_data:
            curr = s_data['current']
            prev = s_data['prev_close']
            change = curr - prev
            pct = (change / prev) * 100 if prev else 0
            currency = s_data['currency']
            
            # 成交額計算
            if currency == 'TWD':
                amount_str = f"{(s_data['volume'] * s_data['vwap'] / 1e8):.1f} 億"
                vol_str = f"{int(s_data['volume']/1000):,} 張"
            else:
                amount_str = f"{(s_data['volume'] * s_data['vwap'] / 1e6):.1f} M"
                vol_str = f"{s_data['volume']:,} 股"

            # 計算相對大盤績效
            rel_to_index = None
            if idx_data:
                idx_pct = ((idx_data['current'] - idx_data['prev_close']) / idx_data['prev_close']) * 100
                rel_to_index = pct - idx_pct
            
            # Metric 顯示
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(f"最新股價 ({currency})", f"{curr:.2f}", f"{change:+.2f} ({pct:+.2f}%)", delta_color="inverse")
            m2.metric("開盤", f"{s_data['open']:.2f}")
            m3.metric("最高", f"{s_data['high']:.2f}")
            m4.metric("最低", f"{s_data['low']:.2f}")
            
            m5, m6, m7, m8 = st.columns(4)
            m5.metric("成交金額", amount_str)
            m6.metric("成交量", vol_str)
            if rel_to_index is not None:
                rel_color = "normal" if rel_to_index >= 0 else "inverse"
                m7.metric("相對大盤強弱", f"{rel_to_index:+.2f}%", delta_color=rel_color)
            else:
                m7.metric("相對大盤", "--")
            m8.metric("昨收", f"{prev:.2f}")
            
            st.divider()
            
            if not s_data['df'].empty:
                # 繪圖
                fig = make_candlestick_chart(s_data['df'], prev, currency, height=550, show_volume=True)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"目前無 {selected_name} 的即時交易數據 (可能是休市中)。")
        else:
            st.error(f"無法取得 {selected_name} 資料，這可能是 Yahoo 阻擋或網路問題。")
    
    with col_index:
        st.markdown(f"### {index_name}")
        if idx_data:
            i_curr = idx_data['current']
            i_prev = idx_data['prev_close']
            i_change = i_curr - i_prev
            i_pct = (i_change / i_prev) * 100 if i_prev else 0
            
            st.metric("點數", f"{i_curr:,.0f}", f"{i_change:+.2f} ({i_pct:+.2f}%)", delta_color="inverse")
            
            if not idx_data['df'].empty:
                mini_fig = make_candlestick_chart(idx_data['df'], i_prev, "", height=300, show_volume=False)
                st.plotly_chart(mini_fig, use_container_width=True)
        else:
            st.warning("指數資料讀取中...")

# 頁腳
try:
    update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
except NameError:
    update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

st.markdown(f"""
    <div class="footer">
        遠東集團 聯合稽核總部 一處戰情室<br>
        開發者：李宗念｜更新時間：{update_time} (台灣時間)
    </div>
""", unsafe_allow_html=True)
