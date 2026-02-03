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

# CSS 強化：更大字體、更好間距、戰情室風格
st.markdown("""
    <style>
        .big-metric { font-size: 2.2rem !important; font-weight: 900; }
        .metric-label { font-size: 1rem !important; }
        .stPlotlyChart { margin-top: 10px; }
        .block-container { padding-top: 1rem; }
    </style>
""", unsafe_allow_html=True)

# === 2. 資料取得（1分鐘K棒 + fast_info）===
@st.cache_data(ttl=30)
def get_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1d", interval="1m", auto_adjust=False)
        info = ticker.fast_info
        
        last_price = info.get('lastPrice') or (df['Close'].iloc[-1] if not df.empty else None)
        prev_close = info.get('previousClose') or (df['Close'].iloc[-2] if len(df) > 1 else None)
        volume = info.get('lastVolume') or df['Volume'].sum()
        
        return {
            "df": df,
            "current": last_price,
            "prev_close": prev_close,
            "volume": volume
        }
    except:
        return None

# === 3. Plotly Candlestick + Volume 圖表（清晰版）===
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
    
    # 台灣風格：紅漲綠跌
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
    
    # 昨收參考線
    fig.add_hline(y=prev_close, line_dash="dash", line_color="#888888", row=1, col=1)
    
    # 成交量（同色）
    colors = ['#d62728' if row['Close'] >= row['Open'] else '#2ca02c' for i, row in df.iterrows()]
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

# 小型大盤圖（也用 Candlestick，更清楚）
def make_mini_index_chart(df, prev_close):
    if df.empty:
        return None
    return make_candlestick_chart(df, prev_close, "加權指數當日走勢", height=300)

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
    col_main, col_index = st.columns([4, 1.5])  # 左大右中
    
    # === 左側：個股主圖 ===
    with col_main:
        if s_data and s_data['current'] is not None:
            curr = s_data['current']
            prev = s_data['prev_close'] or curr
            change = curr - prev
            pct = (change / prev) * 100
            
            # 成交金額估計
            avg_price = s_data['df']['Close'].mean() if not s_data['df'].empty else curr
            amount_billion = (s_data['volume'] * avg_price) / 1e8
            
            # 相對大盤
            rel_to_index = None
            if idx_data and idx_data['current'] is not None:
                idx_pct = ((idx_data['current'] - idx_data['prev_close']) / idx_data['prev_close']) * 100
                rel_to_index = pct - idx_pct
            
            # 指標列
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
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("尚未開盤或無盤中資料")
        else:
            st.error("無法載入個股資料")
    
    # === 右側：大盤對比（中型 Candlestick）===
    with col_index:
        st.markdown("### 🇹🇼 加權指數")
        if idx_data and idx_data['current'] is not None:
            i_curr = idx_data['current']
            i_prev = idx_data['prev_close'] or i_curr
            i_change = i_curr - i_prev
            i_pct = (i_change / i_prev) * 100
            
            st.metric("點數", f"{i_curr:,.0f}", f"{i_change:+.0f} ({i_pct:+.2f}%)", delta_color="inverse")
            
            if not idx_data['df'].empty:
                mini_fig = make_mini_index_chart(idx_data['df'], i_prev)
                st.plotly_chart(mini_fig, use_container_width=True)
            else:
                st.caption("無今日資料")
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
