import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import pytz
from datetime import datetime, timedelta
import numpy as np

# === 1. 系統初始化 ===
st.set_page_config(page_title="遠東集團_聯合稽核總部_一處戰情室", layout="wide")

# 定義台灣時區
tw_tz = pytz.timezone('Asia/Taipei')

# CSS：Apple風格設計 (保持原樣，修復縮排)
st.markdown("""
    <style>
        html, body, [class*="css"]  { font-family: 'Microsoft JhengHei', -apple-system, BlinkMacSystemFont, sans-serif !important; }
        .stApp { background-color: #f9f9f9; }
        .main-title {
            font-size: 2.8rem !important;
            font-weight: 600;
            color: #1d1d1f;
            text-align: center;
            margin-top: 2rem;
            margin-bottom: 3rem;
            letter-spacing: 0.5px;
        }
        div[data-testid="stVerticalBlock"] > div[class*="stVerticalBlock"] > div[class*="stMarkdown"] {
            margin-bottom: 1rem;
        }
        /* 卡片式設計 */
        div[data-testid="stVerticalBlock"] > div[class*="element-container"] {
            background: transparent;
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
st.markdown('<div class="main-title">遠東集團<br>聯合稽核總部 一處戰情室</div>', unsafe_allow_html=True)

# === 2. 資料取得 (優化版：不使用 .info 以加速) ===
@st.cache_data(ttl=60)  # 設定緩存 60 秒
def get_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        
        # 策略：抓取 5 天的資料，這樣一定能算昨收
        # interval="5m" 只能抓最近 60 天，period="5d" 夠用了
        df = ticker.history(period="5d", interval="5m")
        
        if df.empty:
            # 如果抓不到 5分線 (例如剛開盤或週末)，改抓日線
            df = ticker.history(period="5d", interval="1d")
        
        if df.empty:
            return None

        # 取得最新一筆資料
        latest_row = df.iloc[-1]
        current = latest_row['Close']
        
        # 計算昨收 (Previous Close)
        # 邏輯：找到最後一個交易日的"前一天"收盤價
        # 這裡簡化處理：如果 dataframe 跨越多日，取最後一筆之前的收盤價當參考
        # 為了更準確，我們另外抓日線來確認昨收
        try:
            day_df = ticker.history(period="5d", interval="1d")
            if len(day_df) >= 2:
                prev_close = day_df['Close'].iloc[-2] # 倒數第二筆是昨收
            else:
                prev_close = current # 如果沒有昨收，就用當前價代替
        except:
            prev_close = current

        # 計算當日數據
        # 篩選出「今天」的資料 (假設最後一筆是今天)
        last_date = df.index[-1].date()
        today_df = df[df.index.date == last_date]
        
        if today_df.empty:
            today_df = df.iloc[[-1]] # 防呆

        volume = today_df['Volume'].sum()
        open_price = today_df['Open'].iloc[0]
        high = today_df['High'].max()
        low = today_df['Low'].min()
        
        # 計算 VWAP (成交量加權平均價)
        if volume > 0:
            vwap = (today_df['Close'] * today_df['Volume']).sum() / volume
        else:
            vwap = current

        return {
            "df": today_df, # 只傳回今天的 K 線
            "current": current,
            "prev_close": prev_close,
            "volume": volume,
            "open": open_price,
            "high": high,
            "low": low,
            "vwap": vwap
        }
    except Exception as e:
        st.error(f"資料讀取錯誤 ({symbol}): {e}")
        return None

# === 3. Plotly K線圖 ===
def make_candlestick_chart(df, prev_close, height=500, show_volume=True):
    if df.empty:
        return None
    
    # 判斷漲跌顏色
    current_price = df['Close'].iloc[-1]
    
    # 設定圖表列數
    rows = 2 if show_volume else 1
    row_heights = [0.7, 0.3] if show_volume else [1.0]
    
    fig = make_subplots(
        rows=rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights
    )
    
    # K線圖
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='#d62728', increasing_fillcolor='#d62728', # 台股紅漲
        decreasing_line_color='#2ca02c', decreasing_fillcolor='#2ca02c', # 台股綠跌
        name="Price"
    ), row=1, col=1)
    
    # 昨收參考線
    fig.add_hline(y=prev_close, line_dash="dash", line_color="gray", opacity=0.5, row=1, col=1)
    
    # 成交量圖
    if show_volume:
        colors = ['#d62728' if c >= o else '#2ca02c' for c, o in zip(df['Close'], df['Open'])]
        fig.add_trace(go.Bar(
            x=df.index, y=df['Volume'],
            marker_color=colors,
            name="Volume"
        ), row=2, col=1)
    
    # 樣式設定
    fig.update_layout(
        height=height,
        xaxis_rangeslider_visible=False,
        showlegend=False,
        plot_bgcolor='white',
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
        xaxis=dict(showgrid=False)
    )
    
    return fig

# === 4. 主 UI 邏輯 ===
# 股票代碼映射
stock_map = {
    "1402 遠東新": "1402.TW", "1102 亞泥": "1102.TW", "2606 裕民": "2606.TW",
    "1460 宏遠": "1460.TW", "2903 遠百": "2903.TW", "4904 遠傳": "4904.TW", "1710 東聯": "1710.TW"
}

st.sidebar.header("🎯 遠東集團監控")
selected_name = st.sidebar.radio("選擇公司", list(stock_map.keys()))
ticker = stock_map[selected_name]

if st.sidebar.button("🔄 立即更新"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption("資料來源：Yahoo Finance")

# 獲取資料
s_data = get_data(ticker)
idx_data = get_data("^TWII") # 大盤

with st.container():
    col_main, col_index = st.columns([7, 3])
    
    # --- 左側：個股詳情 ---
    with col_main:
        st.markdown(f"## 🔥 {selected_name}")
        
        if s_data:
            curr = s_data['current']
            prev = s_data['prev_close']
            change = curr - prev
            pct = (change / prev) * 100 if prev else 0
            
            # 計算強弱度
            rel_strength = "N/A"
            if idx_data:
                idx_pct = ((idx_data['current'] - idx_data['prev_close']) / idx_data['prev_close']) * 100
                rel_val = pct - idx_pct
                rel_color = "normal" if rel_val > 0 else "inverse"
                
            # 第一排指標
            c1, c2, c3 = st.columns(3)
            c1.metric("最新股價", f"{curr:.2f}", f"{change:+.2f} ({pct:+.2f}%)", delta_color="inverse")
            c2.metric("昨收", f"{prev:.2f}")
            c3.metric("成交量 (張)", f"{int(s_data['volume']/1000):,}")
            
            # 第二排指標
            c4, c5, c6 = st.columns(3)
            c4.metric("最高 / 最低", f"{s_data['high']:.2f} / {s_data['low']:.2f}")
            c5.metric("均價 (VWAP)", f"{s_data['vwap']:.2f}")
            if idx_data:
                c6.metric("相對大盤強弱", f"{rel_val:+.2f}%", delta_color=rel_color)

            st.divider()
            
            # 繪圖
            if not s_data['df'].empty:
                fig = make_candlestick_chart(s_data['df'], prev, height=500)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("暫無 K 線資料")
        else:
            st.error("無法取得即時資料，可能是 Yahoo Finance 暫時限流，請稍後再試。")
    
    # --- 右側：大盤資訊 ---
    with col_index:
        st.markdown("### 🇹🇼 加權指數")
        if idx_data:
            i_curr = idx_data['current']
            i_prev = idx_data['prev_close']
            i_change = i_curr - i_prev
            i_pct = (i_change / i_prev) * 100
            
            st.metric("點數", f"{i_curr:,.0f}", f"{i_change:+.0f} ({i_pct:+.2f}%)", delta_color="inverse")
            
            if not idx_data['df'].empty:
                mini_fig = make_candlestick_chart(idx_data['df'], i_prev, height=300, show_volume=False)
                st.plotly_chart(mini_fig, use_container_width=True)
        else:
            st.warning("讀取中...")

# 頁腳
update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"""
    <div class="footer">
        遠東集團 聯合稽核總部 一處戰情室<br>
        開發者：李宗念｜更新時間：{update_time} (台灣時間)
    </div>
""", unsafe_allow_html=True)
