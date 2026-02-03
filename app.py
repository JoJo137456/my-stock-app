import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime, time, timedelta
import pytz

# === 1. 系統設置與 CSS 美化 ===
st.set_page_config(page_title="遠東集團戰情中心", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

# CSS: 讓 Metric 變更有質感，模擬看盤軟體的卡片式設計
st.markdown("""
    <style>
        html, body, [class*="css"] { font-family: 'Microsoft JhengHei', sans-serif !important; }
        
        /* 調整 Metric 樣式 */
        div[data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700; }
        div[data-testid="stMetricLabel"] { font-size: 0.9rem !important; color: #666; }
        
        /* 調整容器間距 */
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        
        /* 讓圖表更緊湊 */
        div[data-testid="stAltairChart"] { margin-top: -10px; }
    </style>
""", unsafe_allow_html=True)

# === 2. 核心數據邏輯 ===

@st.cache_data(ttl=30)
def get_data_yf(symbol):
    try:
        stock = yf.Ticker(symbol)
        # 取得 intraday
        df = stock.history(period="1d", interval="1m", auto_adjust=False)
        fi = stock.fast_info
        
        # 數據容錯處理
        last_price = fi.last_price
        if last_price is None and not df.empty:
            last_price = df['Close'].iloc[-1]
            
        prev_close = fi.previous_close
        if prev_close is None and not df.empty: 
            # 如果抓不到昨收，勉強用第一筆開盤前推一點點 (這只是保險)
            prev_close = df['Open'].iloc[0]

        # 取得 Open/High/Low (優先用 fast_info，沒有則用 df 統計)
        day_open = fi.open if fi.open else (df['Open'].iloc[0] if not df.empty else 0)
        day_high = fi.day_high if fi.day_high else (df['High'].max() if not df.empty else 0)
        day_low = fi.day_low if fi.day_low else (df['Low'].min() if not df.empty else 0)
        
        vol = fi.last_volume if fi.last_volume else (df['Volume'].sum() if not df.empty else 0)

        return {
            "symbol": symbol,
            "current": last_price,
            "prev_close": prev_close,
            "open": day_open,
            "high": day_high,
            "low": day_low,
            "volume": vol,
            "df": df
        }
    except Exception as e:
        return None

# === 3. 專業圖表繪製 (漸層區域 + 均線 + 量) ===

def draw_chart_combo(df, prev_close):
    if df.empty: return None
    df = df.reset_index()
    
    # 時間欄位統一
    col_name = "Date" if "Date" in df.columns else "Datetime"
    if col_name in df.columns: df.rename(columns={col_name: "Time"}, inplace=True)
    elif 'index' in df.columns: df.rename(columns={'index': "Time"}, inplace=True)
    
    # 時區處理
    if 'Time' in df.columns:
        if df['Time'].dt.tz is None:
            df['Time'] = df['Time'].dt.tz_localize('UTC').dt.tz_convert(tw_tz)
        else:
            df['Time'] = df['Time'].dt.tz_convert(tw_tz)

    # 顏色邏輯：與「前一分鐘」比較 (紅漲綠跌)
    # 或者簡單一點：收 > 開 (紅)，收 < 開 (綠)
    df['Color'] = df.apply(lambda x: '#d62728' if x['Close'] >= x['Open'] else '#2ca02c', axis=1)

    # Y軸動態範圍
    y_min = df['Close'].min()
    y_max = df['Close'].max()
    padding = (y_max - y_min) * 0.1 if y_max != y_min else y_max * 0.01
    y_domain = [y_min - padding, y_max + padding]

    base = alt.Chart(df).encode(x=alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M', grid=True, tickCount=8)))
    
    # 1. 價格區域圖 (Area) - 增加質感
    area = base.mark_area(opacity=0.1, color='#555').encode(
        y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain))
    )
    
    # 2. 價格線 (Line)
    line = base.mark_line(strokeWidth=2.5).encode(
        y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain), axis=alt.Axis(title='股價')),
        color=alt.value('#222') # 深黑色線條
    )
    
    # 3. 昨收基準線 (Grey Dotted Rule) - 你的重點需求
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(
        strokeDash=[6, 4], size=1.5, color='#888'
    ).encode(y='y')

    price_chart = (area + line + rule).properties(height=350)

    # 4. 成交量 (Bar) - 紅綠分明
    vol_chart = base.mark_bar(opacity=0.8).encode(
        y=alt.Y('Volume:Q', axis=alt.Axis(title='量', tickCount=3)),
        color=alt.Color('Color:N', scale=None),
        tooltip=['Time', 'Close', 'Volume']
    ).properties(height=100)

    return alt.vconcat(price_chart, vol_chart, spacing=0).resolve_scale(x='shared')

# === 4. UI 佈局 ===

stock_map = {
    "1402 遠東新": "1402.TW", "1102 亞泥": "1102.TW", "2606 裕民": "2606.TW",
    "1460 宏遠": "1460.TW", "2903 遠百": "2903.TW", "4904 遠傳": "4904.TW", "1710 東聯": "1710.TW"
}

# Sidebar
st.sidebar.title("📈 遠東戰情室")
selected_name = st.sidebar.radio("監控標的", list(stock_map.keys()))
ticker = stock_map[selected_name]
st.sidebar.markdown("---")
st.sidebar.caption(f"系統時間: {datetime.now(tw_tz).strftime('%H:%M:%S')}")

# Main Logic
idx_data = get_data_yf("^TWII") # 大盤
s_data = get_data_yf(ticker)    # 個股

# --- 第一層：大盤與個股 核心概況 ---
col1, col2 = st.columns([1, 2])

with col1:
    with st.container(border=True):
        st.markdown("**🇹🇼 加權指數 (TWII)**")
        if idx_data and idx_data['current']:
            diff = idx_data['current'] - idx_data['prev_close']
            pct = (diff / idx_data['prev_close']) * 100
            color = "normal" # Streamlit 會自動紅綠
            
            st.metric("目前點數", f"{idx_data['current']:,.0f}", f"{diff:+.0f} ({pct:+.2f}%)")
            
            # 大盤簡易強度指標
            amp = (idx_data['high'] - idx_data['low']) / idx_data['prev_close'] * 100
            st.caption(f"今日振幅: {amp:.2f}% | 預估量: 動態計算中")
        else:
            st.warning("資料載入中...")

with col2:
    with st.container(border=True):
        st.markdown(f"**🔥 重點監控：{selected_name}**")
        if s_data and s_data['current']:
            s_diff = s_data['current'] - s_data['prev_close']
            s_pct = (s_diff / s_data['prev_close']) * 100
            
            # 主價格顯示
            st.metric("現價", f"{s_data['current']:.2f}", f"{s_diff:+.2f} ({s_pct:+.2f}%)")
        else:
            st.error("無法取得數據")

# --- 第二層：詳細報價條 (Ticker Tape 風格) ---
# 這裡放置 Open, High, Low, Vol, Amount
if s_data and s_data['current']:
    st.markdown("### 📊 詳細交易數據")
    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        
        # 顏色邏輯：高於昨收紅，低於昨收綠
        def color_txt(val, ref):
            return "red" if val > ref else ("green" if val < ref else "gray")

        # 1. 開盤
        c1.metric("🔔 開盤", f"{s_data['open']:.2f}", delta=round(s_data['open']-s_data['prev_close'], 2), delta_color="inverse")
        
        # 2. 最高
        c2.metric("🔺 最高", f"{s_data['high']:.2f}", delta=round(s_data['high']-s_data['prev_close'], 2), delta_color="inverse")
        
        # 3. 最低
        c3.metric("🔻 最低", f"{s_data['low']:.2f}", delta=round(s_data['low']-s_data['prev_close'], 2), delta_color="inverse")
        
        # 4. 成交量 (張)
        vol_sheet = s_data['volume'] / 1000
        c4.metric("📦 總量 (張)", f"{vol_sheet:,.0f}")
        
        # 5. 預估/成交金額 (億)
        # 用 均價 * 量 概算
        avg_p = (s_data['high'] + s_data['low'] + s_data['current']) / 3
        amt_est = (s_data['volume'] * avg_p) / 100000000
        c5.metric("💎 金額 (億)", f"{amt_est:.2f}")

    # --- 第三層：趨勢圖表 ---
    st.markdown("### 📈 走勢分析")
    if not s_data['df'].empty:
        st.altair_chart(draw_chart_combo(s_data['df'], s_data['prev_close']), use_container_width=True)
    else:
        st.info("盤前或無交易數據，請稍後...")

else:
    st.write("等待數據連線...")
