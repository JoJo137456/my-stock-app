import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import pytz
from datetime import datetime
import numpy as np

# === 1. 系統初始化 ===
st.set_page_config(page_title="遠東集團戰情中心", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

# CSS 美化 + 確保指標完整顯示
st.markdown("""
    <style>
        .block-container { padding-top: 3rem !important; padding-bottom: 2rem; }
        .stMetric { margin-top: 10px !important; }
        .stPlotlyChart { margin-top: 20px; }
        div[data-testid="metric-container"] { padding-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# === 2. 資料取得 ===
@st.cache_data(ttl=30)
def get_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
        current = info.get('currentPrice') or info.get('regularMarketPrice')
        
        df = ticker.history(period="1d", interval="5m")
        if df.empty:
            df = ticker.history(period="1d", interval="15m")
        
        if current is None and not df.empty:
            current = df['Close'].iloc[-1]
        
        volume = df['Volume'].sum() if not df.empty else 0
        
        if not df.empty:
            open_price = df['Open'].iloc[0]
            high = df['High'].max()
            low = df['Low'].min()
            typical_price = (df['High'] + df['Low'] + df['Close']) / 3
            vwap = (typical_price * df['Volume']).sum() / df['Volume'].sum() if volume > 0 else df['Close'].mean()
        else:
            open_price = high = low = vwap = current
        
        if current is None:
            raise ValueError("無法取得最新價格")
        
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
        st.error(f"載入 {symbol} 失敗：{str(e)}")
        return None

# === 3. Plotly K線圖（恢復 K線 + 新增灰白交替水平色塊）===
def make_candlestick_chart(df, prev_close, height=500, show_volume=True):
    if df.empty:
        return None
    
    # 整體漲跌背景（淡紅/淡綠）
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
    
    # K線（紅漲綠跌實心）
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
    
    # 昨收虛線
    fig.add_hline(y=prev_close, line_dash="dash", line_color="#888888", row=1, col=1)
    
    # === 新增：灰白交替水平色塊（方便閱讀價格區間）===
    y_min = df['Low'].min()
    y_max = df['High'].max()
    padding = (y_max - y_min) * 0.05
    y_range = [y_min - padding, y_max + padding]
    
    # 計算合適的價格間隔（類似券商自動格線）
    price_range = y_max - y_min
    if price_range == 0:
        interval = 0.1
    else:
        interval = 10 ** np.floor(np.log10(price_range / 5))
        interval = max(0.05, round(interval, 2))
    
    # 從下往上取整開始
    start_y = np.floor(y_min / interval) * interval
    end_y = np.ceil(y_max / interval) * interval
    
    prices = np.arange(start_y, end_y + interval, interval)
    
    for i, price in enumerate(prices[:-1]):
        color = "rgba(240, 240, 240, 0.6)" if i % 2 == 0 else "rgba(255, 255, 255, 0.8)"
        fig.add_shape(
            type="rect",
            x0=df.index[0], x1=df.index[-1],
            y0=price, y1=prices[i+1],
            fillcolor=color,
            line_width=0,
            layer="below",
            row=1, col=1
        )
    
    # 整體漲跌淡色覆蓋在上層（讓交替格仍可見）
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
    
    # 成交量（個股顯示，同色）
    if show_volume:
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
        plot_bgcolor='white',
        margin=dict(l=40, r=40, t=40, b=40),
        yaxis=dict(range=y_range)
    )
    
    fig.update_xaxes(
        tickformat='%H:%M',
        title_text="時間" if show_volume else "",
        row=rows, col=1
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

s_data = get_data(ticker)
idx_data = get_data("^TWII")

with st.container(border=True):
    col_main, col_index = st.columns([4, 1.5])
    
    with col_main:
        st.markdown(f"## 🔥 {selected_name}　當日走勢")
        
        if s_data:
            curr = s_data['current']
            prev = s_data['prev_close']
            change = curr - prev
            pct = (change / prev) * 100 if prev else 0
            
            amount_billion = (s_data['volume'] * s_data['vwap']) / 1e8 if s_data['volume'] > 0 else 0
            
            rel_to_index = None
            if idx_data:
                idx_pct = ((idx_data['current'] - idx_data['prev_close']) / idx_data['prev_close']) * 100
                rel_to_index = pct - idx_pct
            
            # 第一排
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("最新股價", f"{curr:.2f}", f"{change:+.2f} ({pct:+.2f}%)", delta_color="inverse")
            m2.metric("開盤", f"{s_data['open']:.2f}")
            m3.metric("最高", f"{s_data['high']:.2f}")
            m4.metric("最低", f"{s_data['low']:.2f}")
            m5.metric("均價", f"{s_data['vwap']:.2f}")
            
            # 第二排
            m6, m7, m8, m9 = st.columns(4)
            m6.metric("成交金額 (億)", f"{amount_billion:.1f}")
            m7.metric("總量 (張)", f"{int(s_data['volume']/1000):,}")
            if rel_to_index is not None:
                rel_color = "normal" if rel_to_index >= 0 else "inverse"
                m8.metric("相對大盤", f"{rel_to_index:+.2f}%", delta_color=rel_color)
            m9.metric("昨收", f"{prev:.2f}")
            
            st.divider()
            
            if not s_data['df'].empty:
                fig = make_candlestick_chart(s_data['df'], prev, height=550, show_volume=True)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("今日尚無K線資料，但價格已更新")
        else:
            st.error("個股資料載入失敗")
    
    with col_index:
        st.markdown("### 🇹🇼 加權指數")
        if idx_data:
            i_curr = idx_data['current']
            i_prev = idx_data['prev_close']
            i_change = i_curr - i_prev
            i_pct = (i_change / i_prev) * 100 if i_prev else 0
            
            st.metric("點數", f"{i_curr:,.0f}", f"{i_change:+.0f} ({i_pct:+.2f}%)", delta_color="inverse")
            
            if not idx_data['df'].empty:
                mini_fig = make_candlestick_chart(idx_data['df'], i_prev, height=350, show_volume=False)
                st.plotly_chart(mini_fig, use_container_width=True)

# 頁腳
st.markdown("---")
st.markdown(
    f"<div style='text-align: center; color: #888; font-size: 0.9rem;'>"
    f"遠東集團戰情中心｜更新時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} (台灣時間)"
    f"</div>",
    unsafe_allow_html=True
)
