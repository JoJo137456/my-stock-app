import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import pytz # 用來處理時區

# 設定台灣時區
tw_tz = pytz.timezone('Asia/Taipei')

# === 1. 網頁基本設定 ===
st.set_page_config(page_title="遠東集團戰情中心", layout="wide")

# === 2. 定義遠東集團關注清單 ===
stock_map = {
    "1402 遠東新": "1402.TW",
    "1102 亞泥": "1102.TW",
    "2606 裕民": "2606.TW",
    "1460 宏遠": "1460.TW",
    "2903 遠百": "2903.TW",
    "4904 遠傳": "4904.TW",
    "1710 東聯": "1710.TW",
    "6997 博弘": "6997.TWO"
}

# === 3. 數據抓取與計算核心 ===

@st.cache_data(ttl=60)
def get_quote_data(symbol):
    """抓取即時報價與分時走勢"""
    try:
        stock = yf.Ticker(symbol)
        # 抓取今日分時數據 (1分鐘頻率)
        df_intraday = stock.history(period="1d", interval="1m")
        # 抓取日線數據 (為了拿昨收)
        df_daily = stock.history(period="5d") 
        return df_intraday, df_daily, stock.info
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), {}

def calculate_metrics(df_intraday, df_daily, info):
    """計算關鍵指標"""
    if df_intraday.empty: return None

    current_price = df_intraday['Close'].iloc[-1]
    
    # 優先從 info 抓昨收，抓不到就從日線推算
    prev_close = info.get('previousClose')
    if prev_close is None and len(df_daily) >= 2:
        prev_close = df_daily['Close'].iloc[-2]
    if prev_close is None: prev_close = df_intraday['Open'].iloc[0] # 防呆

    change = current_price - prev_close
    pct_change = (change / prev_close) * 100
    
    high = df_intraday['High'].max()
    low = df_intraday['Low'].min()
    open_price = df_intraday['Open'].iloc[0]
    volume = df_intraday['Volume'].sum()
    
    # 計算當日均價 (VWAP)
    total_value = (df_intraday['Close'] * df_intraday['Volume']).sum()
    total_volume = df_intraday['Volume'].sum()
    avg_price = total_value / total_volume if total_volume > 0 else current_price

    return {"current": current_price, "prev_close": prev_close, "change": change,
            "pct_change": pct_change, "high": high, "low": low,
            "open": open_price, "volume": volume, "avg_price": avg_price}

# === 4. 側邊欄：控制中心 ===
st.sidebar.header("🎯 監控標的選擇")
selected_name = st.sidebar.radio("請選擇公司：", list(stock_map.keys()))
ticker = stock_map[selected_name]

st.sidebar.markdown("---")
# 這裡是你原本要求的地方
st.sidebar.caption(f"✅ 系統連線正常\n👤 開發者：李宗念")

# === 5. 頂部戰情儀表 ===
col_title, col_index = st.columns([3, 1])
with col_title:
    st.title("🏢 遠東集團_聯稽一處戰情指揮中心")
    st.markdown(f"### 🔥 目前監控：**{selected_name}**")

with col_index:
    st.markdown("##### 🇹🇼 台灣加權指數")
    idx_intra, idx_daily, idx_info = get_quote_data("^TWII")
    if idx_intra.empty:
        st.warning("大盤連線中...")
    else:
        idx_metrics = calculate_metrics(idx_intra, idx_daily, idx_info)
        if idx_metrics:
            st.metric("加權指數", f"{idx_metrics['current']:,.0f}", 
                      f"{idx_metrics['change']:+.0f} ({idx_metrics['pct_change']:+.2f}%)",
                      delta_color="inverse")
            st.line_chart(idx_intra['Close'], height=80)

st.markdown("---")

# === 6. 主畫面：個股詳細戰情 ===
df_1m, df_1d, info = get_quote_data(ticker)

if df_1m.empty:
    st.error(f"⚠️ 無法取得 {selected_name} 的即時數據，請稍後再試。")
else:
    metrics = calculate_metrics(df_1m, df_1d, info)
    
    # 儀表板數據呈現
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 目前股價", f"{metrics['current']:.2f}", f"{metrics['change']:+.2f} ({metrics['pct_change']:+.2f}%)", delta_color="inverse")
    c2.metric("📊 當日均價 (VWAP)", f"{metrics['avg_price']:.2f}")
    c3.metric("📦 總成交量 (張)", f"{metrics['volume']/1000:,.0f}")
    c4.metric("⚖️ 昨收價", f"{metrics['prev_close']:.2f}")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("🔔 開盤價", f"{metrics['open']:.2f}")
    c6.metric("🔺 最高價", f"{metrics['high']:.2f}")
    c7.metric("🔻 最低價", f"{metrics['low']:.2f}")
    amplitude = ((metrics['high'] - metrics['low']) / metrics['prev_close']) * 100
    c8.metric("〰️ 當日振幅", f"{amplitude:.2f}%")

    st.markdown("---")

    # 專業走勢圖 (Altair)
    st.subheader("📈 今日即時走勢 (Trend & Volume)")
    chart_data = df_1m.reset_index()
    chart_data.rename(columns={"index": "Time", "Datetime": "Time"}, inplace=True)
    
    # 價格線 (紅色)
    price_chart = alt.Chart(chart_data).mark_line(color='#FF4B4B').encode(
        x=alt.X('Time:T', axis=alt.Axis(title='時間', format='%H:%M')),
        y=alt.Y('Close:Q', scale=alt.Scale(zero=False), axis=alt.Axis(title='股價')),
        tooltip=['Time', 'Close', 'Volume']
    ).properties(height=350)
    
    # 均價線 (橘色虛線)
    avg_line = alt.Chart(pd.DataFrame({'y': [metrics['avg_price']]})).mark_rule(strokeDash=[5, 5], color='#FFA500').encode(
        y='y', tooltip=alt.value(f"均價: {metrics['avg_price']:.2f}"))

    # 成交量圖 (下方柱狀)
    vol_chart = alt.Chart(chart_data).mark_bar(color='#aaaaaa').encode(
        x=alt.X('Time:T', axis=None),
        y=alt.Y('Volume:Q', axis=alt.Axis(title='成交量')),
        tooltip=['Time', 'Volume']
    ).properties(height=100)

    final_chart = alt.vconcat(price_chart + avg_line, vol_chart).resolve_scale(x='shared')
    st.altair_chart(final_chart, use_container_width=True)

# === 頁尾 (這裡是最顯眼的新位置！) ===
st.markdown("---")
current_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"""
<div style="text-align: center; color: gray; font-size: 0.9em;">
    <b>遠東集團_聯稽一處戰情指揮中心</b> | 開發者：<b>李宗念</b><br>
    資料來源：Yahoo Finance 即時報價 | 最後更新：{current_time} (台灣時間)
</div>
""", unsafe_allow_html=True)
