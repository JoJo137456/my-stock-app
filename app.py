import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime
import pytz

# 設定台灣時區
tw_tz = pytz.timezone('Asia/Taipei')

# === 1. 網頁基本設定 ===
st.set_page_config(page_title="遠東集團戰情中心", layout="wide")

# === ⚠️ 全站字體優化 ===
st.markdown("""
    <style>
        html, body, [class*="css"] {
            font-family: 'Microsoft JhengHei', '微軟正黑體', sans-serif !important;
        }
    </style>
""", unsafe_allow_html=True)

# === 2. 定義關注清單 ===
stock_map = {
    "1402 遠東新": "1402.TW",
    "1102 亞泥": "1102.TW",
    "2606 裕民": "2606.TW",
    "1460 宏遠": "1460.TW",
    "2903 遠百": "2903.TW",
    "4904 遠傳": "4904.TW",
    "1710 東聯": "1710.TW"
}

# === 3. 數據核心函數 (升級版：支援多種週期) ===

@st.cache_data(ttl=60)
def get_quote_data(symbol):
    """抓取即時報價與基礎日線(算昨收用)"""
    try:
        stock = yf.Ticker(symbol)
        df_intraday = stock.history(period="1d", interval="1m")
        df_daily = stock.history(period="5d") 
        return df_intraday, df_daily, stock.info
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), {}

@st.cache_data(ttl=300) # 歷史資料快取久一點(5分鐘)
def get_history_chart_data(symbol, time_range):
    """根據使用者選擇的時間，抓取對應的圖表資料"""
    stock = yf.Ticker(symbol)
    
    if time_range == "⚡ 今日即時 (1分K)":
        return stock.history(period="1d", interval="1m")
    elif time_range == "📅 近 5 天 (5分K)":
        return stock.history(period="5d", interval="5m")
    elif time_range == "🗓️ 近 1 個月 (日K)":
        return stock.history(period="1mo", interval="1d")
    elif time_range == "📆 近 6 個月 (日K)":
        return stock.history(period="6mo", interval="1d")
    else:
        return stock.history(period="1d", interval="1m")

def calculate_metrics(df_intraday, df_daily, info):
    """計算上方儀表板的關鍵數字"""
    if df_intraday.empty: return None

    current_price = df_intraday['Close'].iloc[-1]
    
    prev_close = info.get('previousClose')
    if prev_close is None and len(df_daily) >= 2:
        prev_close = df_daily['Close'].iloc[-2]
    if prev_close is None: prev_close = df_intraday['Open'].iloc[0]

    change = current_price - prev_close
    pct_change = (change / prev_close) * 100
    
    high = df_intraday['High'].max()
    low = df_intraday['Low'].min()
    open_price = df_intraday['Open'].iloc[0]
    volume = df_intraday['Volume'].sum()
    
    total_value = (df_intraday['Close'] * df_intraday['Volume']).sum()
    total_volume = df_intraday['Volume'].sum()
    avg_price = total_value / total_volume if total_volume > 0 else current_price

    return {
        "current": current_price, "prev_close": prev_close, "change": change,
        "pct_change": pct_change, "high": high, "low": low,
        "open": open_price, "volume": volume, "avg_price": avg_price
    }

# === 4. 側邊欄 ===
st.sidebar.header("🎯 監控標的選擇")
selected_name = st.sidebar.radio("請選擇公司：", list(stock_map.keys()))
ticker = stock_map[selected_name]
st.sidebar.markdown("---")
st.sidebar.caption(f"✅ 系統連線正常\n👤 開發者：李宗念")

# === 5. 頂部戰情儀表 (HUD) ===
col_title, col_index = st.columns([2.5, 1.5])

with col_title:
    st.title("🏢 遠東集團_聯稽一處戰情指揮中心")
    st.markdown(f"### 🔥 目前監控：**{selected_name}**")

with col_index:
    # --- 右上角：大盤指數 ---
    st.markdown("##### 🇹🇼 台灣加權指數")
    idx_intra, idx_daily, idx_info = get_quote_data("^TWII")
    
    if idx_intra.empty:
        st.warning("大盤連線中...")
    else:
        idx_metrics = calculate_metrics(idx_intra, idx_daily, idx_info)
        if idx_metrics:
            st.metric(
                "加權指數", 
                f"{idx_metrics['current']:,.0f}", 
                f"{idx_metrics['change']:+.0f} ({idx_metrics['pct_change']:+.2f}%)",
                delta_color="inverse"
            )
            idx_color = '#FF4B4B' if idx_metrics['change'] >= 0 else '#00C805'
            idx_data = idx_intra.reset_index()
            idx_chart = alt.Chart(idx_data).mark_line(color=idx_color, strokeWidth=2).encode(
                x=alt.X('Datetime:T', axis=None), 
                y=alt.Y('Close:Q', scale=alt.Scale(zero=False), axis=None), 
                tooltip=['Datetime', 'Close']
            ).properties(height=60, width='container')
            st.altair_chart(idx_chart, use_container_width=True)

st.markdown("---")

# === 6. 主畫面：個股詳細戰情 ===

# 1. 先抓基本即時資料 (算儀表板數字用)
df_1m, df_1d, info = get_quote_data(ticker)

if df_1m.empty:
    st.error(f"⚠️ 無法取得 {selected_name} 的即時數據。")
else:
    metrics = calculate_metrics(df_1m, df_1d, info)
    
    # 2. 顯示數據儀表板
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

    # === 🌟 新功能：歷史資料切換 ===
    st.subheader("📈 股價走勢分析")
    
    # 這裡就是時光機按鈕
    time_options = ["⚡ 今日即時 (1分K)", "📅 近 5 天 (5分K)", "🗓️ 近 1 個月 (日K)", "📆 近 6 個月 (日K)"]
    selected_time = st.radio("選擇時間範圍：", time_options, horizontal=True)

    # 根據選擇抓取對應資料
    chart_df = get_history_chart_data(ticker, selected_time)

    if not chart_df.empty:
        chart_data = chart_df.reset_index()
        # 處理欄位名稱差異 (日線叫 Date, 分鐘線叫 Datetime)
        if 'Date' in chart_data.columns:
            chart_data.rename(columns={"Date": "Time"}, inplace=True)
        else:
            chart_data.rename(columns={"Datetime": "Time"}, inplace=True)

        # 決定顏色 (今日看漲跌，歷史統一用藍色系比較專業)
        if selected_time == "⚡ 今日即時 (1分K)":
            line_color = '#FF4B4B' if metrics['change'] >= 0 else '#00C805'
            time_format = '%H:%M' # 分鐘格式
        else:
            line_color = '#0068C9' # 專業藍
            time_format = '%Y-%m-%d' # 日期格式

        # 繪圖
        base = alt.Chart(chart_data).encode(x=alt.X('Time:T', axis=alt.Axis(title='時間', format=time_format)))

        # 價格線
        line = base.mark_line(color=line_color).encode(
            y=alt.Y('Close:Q', scale=alt.Scale(zero=False), axis=alt.Axis(title='股價')),
            tooltip=['Time', 'Close', 'Volume']
        ).properties(height=350)

        # 歷史均線 (如果是看日線，我們畫一條 20日均線)
        if "日K" in selected_time:
            chart_data['MA20'] = chart_data['Close'].rolling(window=20).mean()
            ma_line = base.mark_line(color='#FFA500', strokeDash=[5, 5]).encode(
                y='MA20', tooltip=['Time', 'MA20']
            )
            final_chart = line + ma_line
        
        # 今日均價 (如果是看今日，畫 VWAP)
        elif selected_time == "⚡ 今日即時 (1分K)":
            avg_line = alt.Chart(pd.DataFrame({'y': [metrics['avg_price']]})).mark_rule(strokeDash=[5, 5], color='#FFA500').encode(
                y='y', tooltip=alt.value(f"均價: {metrics['avg_price']:.2f}")
            )
            final_chart = line + avg_line
        else:
            final_chart = line

        # 下方成交量
        vol = base.mark_bar(color='#cccccc').encode(
            y=alt.Y('Volume:Q', axis=alt.Axis(title='成交量')),
            tooltip=['Time', 'Volume']
        ).properties(height=100)

        # 組合
        combined = alt.vconcat(final_chart, vol).resolve_scale(x='shared')
        st.altair_chart(combined, use_container_width=True)
    else:
        st.info("尚無此區間資料")

# === 頁尾 ===
st.markdown("---")
current_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"""
<div style="text-align: center; color: gray; font-size: 0.9em; font-family: 'Microsoft JhengHei', sans-serif;">
    <b>遠東集團_聯稽一處戰情指揮中心</b> | 開發者：<b>李宗念</b><br>
    資料來源：Yahoo Finance 即時報價 | 最後更新：{current_time} (台灣時間)
</div>
""", unsafe_allow_html=True)
