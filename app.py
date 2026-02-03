import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
import numpy as np  # 新增：用於顏色判斷
from datetime import datetime, time, timedelta
import pytz

# === 1. 系統初始化 ===
st.set_page_config(page_title="遠東集團戰情中心", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

# CSS 優化：強化戰情室風格 + 讓圖表更舒適
st.markdown("""
    <style>
        html, body, [class*="css"] { font-family: 'Microsoft JhengHei', sans-serif !important; }
        div[data-testid="stMetricValue"] { font-size: 2rem !important; font-weight: 800; color: #333; }
        div[data-testid="stMetricLabel"] { font-size: 1rem !important; }
        .stAlert { font-size: 0.9rem; }
    </style>
""", unsafe_allow_html=True)

# === 2. 核心邏輯與計算 ===
def get_market_progress():
    now = datetime.now(tw_tz)
    market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
    market_close = now.replace(hour=13, minute=30, second=0, microsecond=0)
   
    if now < market_open:
        return 0.0
    elif now > market_close:
        return 1.0
    else:
        total_minutes = 270
        elapsed = (now - market_open).seconds / 60
        return max(0.01, elapsed / total_minutes)

@st.cache_data(ttl=30)
def get_data_yf(symbol):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period="1d", interval="1m", auto_adjust=False)
        fi = stock.fast_info
        last_price = fi.last_price
        prev_close = fi.previous_close
       
        if last_price is None and not df.empty:
            last_price = df['Close'].iloc[-1]
           
        return {
            "symbol": symbol,
            "current": last_price,
            "prev_close": prev_close,
            "df": df,
            "volume": fi.last_volume if fi.last_volume else (df['Volume'].sum() if not df.empty else 0)
        }
    except Exception as e:
        st.error(f"載入 {symbol} 失敗：{e}")
        return None

# === 3. 新增：Candlestick + Volume 圖表 (更接近 Yahoo Finance) ===
def draw_candlestick_combo(df, prev_close, price_height=350, vol_height=100):
    if df.empty:
        return None
    
    df = df.reset_index().copy()
    
    # 時間欄位統一處理
    if 'Datetime' in df.columns:
        df.rename(columns={'Datetime': 'Time'}, inplace=True)
    elif 'Date' in df.columns:
        df.rename(columns={'Date': 'Time'}, inplace=True)
    else:
        df.rename(columns={'index': 'Time'}, inplace=True)
    
    # 時區處理
    if df['Time'].dt.tz is None:
        df['Time'] = df['Time'].dt.tz_localize('UTC').dt.tz_convert(tw_tz)
    else:
        df['Time'] = df['Time'].dt.tz_convert(tw_tz)
    
    # 台灣慣例：漲紅跌綠
    df['color'] = np.where(df['Close'] >= df['Open'], '#d62728', '#2ca02c')  # 紅漲綠跌
    
    base = alt.Chart(df).encode(
        x=alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M', tickCount=8))
    )
    
    # 高低價線
    high_low = base.mark_rule(strokeWidth=1).encode(
        y='Low:Q',
        y2='High:Q',
        color=alt.Color('color:N', scale=None, legend=None)
    )
    
    # 陰陽燭實體
    candle_body = base.mark_bar(width=8).encode(
        y='Open:Q',
        y2='Close:Q',
        color=alt.Color('color:N', scale=None, legend=None)
    )
    
    # 昨收參考線
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(
        strokeDash=[6,4], strokeWidth=2, color='#888888'
    ).encode(y='y')
    
    price_chart = (high_low + candle_body + rule).properties(
        height=price_height,
        title=alt.TitleParams(text="股價走勢", anchor='middle')
    )
    
    # 成交量（同色）
    vol_chart = base.mark_bar().encode(
        y=alt.Y('Volume:Q', axis=alt.Axis(title='成交量')),
        color=alt.Color('color:N', scale=None, legend=None)
    ).properties(height=vol_height)
    
    return alt.vconcat(price_chart, vol_chart, spacing=5).resolve_scale(x='shared')

# 小型 sparkline（用於大盤）
def draw_mini_sparkline(df, prev_close):
    if df.empty: return None
    df = df.reset_index().copy()
    
    if 'Datetime' in df.columns:
        df.rename(columns={'Datetime': 'Time'}, inplace=True)
    elif 'Date' in df.columns:
        df.rename(columns={'Date': 'Time'}, inplace=True)
    else:
        df.rename(columns={'index': 'Time'}, inplace=True)
    
    last_price = df['Close'].iloc[-1]
    line_color = '#d62728' if last_price >= prev_close else '#2ca02c'
    
    chart = alt.Chart(df).mark_line(strokeWidth=2.5, color=line_color).encode(
        x=alt.X('Time:T', axis=None),
        y=alt.Y('Close:Q', axis=None)
    ).properties(height=70, width=200)
    
    return chart

# === 4. 主程式 UI（調整版：個股大圖左側，大盤小圖右側，符合你「右上角大盤對比」需求）===
stock_map = {
    "1402 遠東新": "1402.TW", "1102 亞泥": "1102.TW", "2606 裕民": "2606.TW",
    "1460 宏遠": "1460.TW", "2903 遠百": "2903.TW", "4904 遠傳": "4904.TW", "1710 東聯": "1710.TW"
}

st.sidebar.header("🎯 遠東集團監控")
selected_name = st.sidebar.radio("選擇公司", list(stock_map.keys()))
ticker = stock_map[selected_name]
st.sidebar.caption("資料來源：Yahoo Finance（延遲約15-20分鐘）")

# 先載入大盤資料（共用）
idx_data = get_data_yf("^TWII")

with st.container(border=True):
    # 左大右小：個股主要走勢在大左側，大盤在右側（類似 Yahoo Finance 右上角小圖概念）
    col_main, col_index = st.columns([4, 1.3])
    
    # === 左側：選定個股（大圖 + 詳細指標）===
    with col_main:
        st.markdown(f"### 🔥 {selected_name}　當日走勢")
        s_data = get_data_yf(ticker)
        
        if s_data and s_data['current'] is not None:
            curr = s_data['current']
            prev = s_data['prev_close']
            change = curr - prev
            pct = (change / prev) * 100 if prev else 0
            
            # 計算成交金額（億）
            avg_price = s_data['df']['Close'].mean() if not s_data['df'].empty else curr
            amount_est = (s_data['volume'] * avg_price) / 1e8
            
            # 與大盤比較（如果大盤資料可用）
            rel_to_index = None
            if idx_data and idx_data['current'] is not None:
                idx_pct = ((idx_data['current'] - idx_data['prev_close']) / idx_data['prev_close']) * 100
                rel_to_index = pct - idx_pct
            
            # 指標列
            mcols = st.columns([2, 1.5, 1.5, 1.5, 1.5])
            mcols[0].metric("最新股價", f"{curr:.2f}", f"{change:+.2f} ({pct:+.2f}%)", delta_color="inverse")
            mcols[1].metric("成交金額 (億)", f"{amount_est:.1f}")
            mcols[2].metric("總量 (張)", f"{s_data['volume']/1000:,.0f}")
            if rel_to_index is not None:
                color = "normal" if rel_to_index >= 0 else "inverse"
                mcols[3].metric("相對大盤", f"{rel_to_index:+.2f}%", delta_color=color)
            mcols[4].metric("昨收", f"{prev:.2f}")
            
            st.divider()
            
            # 大 Candlestick 圖
            if not s_data['df'].empty:
                chart = draw_candlestick_combo(s_data['df'], prev, price_height=380, vol_height=120)
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("今日尚未開盤或無盤中資料")
        else:
            st.error("無法取得個股資料，請稍後重試")
    
    # === 右側：加權指數（小圖 + 簡要指標）===
    with col_index:
        st.markdown("### 🇹🇼 加權指數")
        
        if idx_data and idx_data['current'] is not None:
            i_curr = idx_data['current']
            i_prev = idx_data['prev_close']
            i_change = i_curr - i_prev
            i_pct = (i_change / i_prev) * 100 if i_prev else 0
            
            st.metric("點數", f"{i_curr:,.0f}", f"{i_change:+.0f} ({i_pct:+.2f}%)", delta_color="inverse")
            
            # 小 sparkline
            if not idx_data['df'].empty:
                st.altair_chart(draw_mini_sparkline(idx_data['df'], i_prev), use_container_width=True)
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
