import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import pytz
from datetime import datetime

# === 1. 系統初始化 ===
st.set_page_config(page_title="遠東集團戰情中心", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

# CSS 美化
st.markdown("""
    <style>
        .big-metric { font-size: 2.2rem !important; font-weight: 900; }
        .metric-label { font-size: 1rem !important; }
        .stPlotlyChart { margin-top: 10px; }
        .block-container { padding-top: 1rem; }
    </style>
""", unsafe_allow_html=True)

# === 2. 強化版資料取得（更穩健）===
@st.cache_data(ttl=30)
def get_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        
        # 先取基本資訊（昨收、最新價）
        info = ticker.info
        prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
        current = info.get('currentPrice') or info.get('regularMarketPrice')
        
        # 嘗試取 5m K棒（最穩定）
        df = ticker.history(period="1d", interval="5m")
        if df.empty:
            # fallback 15m
            df = ticker.history(period="1d", interval="15m")
        
        # 如果 info 沒最新價，用 df 補
        if current is None and not df.empty:
            current = df['Close'].iloc[-1]
            if prev_close is None:
                prev_close = df['Open'].iloc[0]  # 或用前一天，但簡化
        
        volume = df['Volume'].sum() if not df.empty else 0
        
        if current is None:
            raise ValueError("無法取得最新價格")
        
        return {
            "df": df,
            "current": current,
            "prev_close": prev_close or current,
            "volume": volume
        }
    except Exception as e:
        st.error(f"載入 {symbol} 失敗：{str(e)}")
        return None

# === 3. Plotly K線圖 ===
def make_candlestick_chart(df, prev_close, title, height=500):
    if df.empty:
        return None
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(title, "成交量"),
        row_heights=[0.7, 0.3]
    )
    
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        increasing_line_color='#d62728', increasing_fillcolor='#d62728',
        decreasing_line_color='#2ca02c', decreasing_fillcolor='#2ca02c',
        name="K線"
    ), row=1, col=1)
    
    fig.add_hline(y=prev_close, line_dash="dash", line_color="#888888", row=1, col=1)
    
    colors = ['#d62728' if row['Close'] >= row['Open'] else '#2ca02c' for _, row in df.iterrows()]
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['Volume'],
        marker_color=colors,
        name="成交量"
    ), row=2, col=1)
    
    fig.update_layout(
        height=height,
        xaxis_rangeslider_visible=False,
        showlegend=False,
        margin=dict(l=40, r=40, t=60, b=40),
        title_text=title,
        title_x=0.5
    )
    
    fig.update_xaxes(
        title_text="時間",
        tickformat='%H:%M',
        row=2, col=1
    )
    
    return fig

# === 4. 主 UI ===
stock_map = {
    "1402 遠東新": "1402.TW", "1102 亞泥": "1102.TW", "2606 裕民": "2606.TW",
    "1460 宏遠": "1460.TW", "2903 遠百": "2903.TW", "4904 遠傳": "4904.TW", "1710 東聯": "1710.TW"
}

st.sidebar.header("🎯 遠東集團監控")
selected_name = st.sidebar.radio("選擇公司", list(stock_map.keys()))
ticker = stock_map[selected_name]
st.sidebar.caption("資料來源：Yahoo Finance（延遲約15-20分鐘）｜每30秒自動更新")

# 載入資料
s_data = get_data(ticker)
idx_data = get_data("^TWII")

with st.container(border=True):
    col_main, col_index = st.columns([4, 1.5])
    
    # 左側：個股
    with col_main:
        if s_data:
            curr = s_data['current']
            prev = s_data['prev_close']
            change = curr - prev
            pct = (change / prev) * 100 if prev else 0
            
            avg_price = s_data['df']['Close'].mean() if not s_data['df'].empty else curr
            amount_billion = (s_data['volume'] * avg_price) / 1e8
            
            rel_to_index = None
            if idx_data:
                idx_pct = ((idx_data['current'] - idx_data['prev_close']) / idx_data['prev_close']) * 100
                rel_to_index = pct - idx_pct
            
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("最新股價", f"{curr:.2f}", f"{change:+.2f} ({pct:+.2f}%)", delta_color="inverse")
            m2.metric("成交金額 (億)", f"{amount_billion:.1f}")
            m3.metric("總量 (張)", f"{int(s_data['volume']/1000):,}")
            if rel_to_index is not None:
                rel_color = "normal" if rel_to_index >= 0 else "inverse"
                m4.metric("相對大盤", f"{rel_to_index:+.2f}%", delta_color=rel_color)
            m5.metric("昨收", f"{prev:.2f}")
            
            st.markdown(f"### {selected_name}　當日走勢")
            
            if not s_data['df'].empty:
                fig = make_candlestick_chart(s_data['df'], prev, f"{selected_name} 當日走勢", height=550)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("無K線資料，但價格已更新")
            else:
                st.info("今日尚無K線資料（可能尚未開盤或資料延遲），但最新價格已顯示")
        else:
            st.error("個股資料載入失敗，請稍後重試或檢查網路")
    
    # 右側：大盤
    with col_index:
        st.markdown("### 🇹🇼 加權指數")
        if idx_data:
            i_curr = idx_data['current']
            i_prev = idx_data['prev_close']
            i_change = i_curr - i_prev
            i_pct = (i_change / i_prev) * 100 if i_prev else 0
            
            st.metric("點數", f"{i_curr:,.0f}", f"{i_change:+.0f} ({i_pct:+.2f}%)", delta_color="inverse")
            
            if not idx_data['df'].empty:
                mini_fig = make_candlestick_chart(idx_data['df'], i_prev, "加權指數當日走勢", height=350)
                if mini_fig:
                    st.plotly_chart(mini_fig, use_container_width=True)
        else:
            st.warning("大盤資料載入中...")

# 頁腳
st.markdown("---")
st.markdown(
    f"<div style='text-align: center; color: #888; font-size: 0.9rem;'>"
    f"遠東集團戰情中心｜更新時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} (台灣時間)"
    f"</div>",
    unsafe_allow_html=True
)
