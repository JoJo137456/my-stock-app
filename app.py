import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

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

# === 3. 抓取數據函數 ===

# A. 抓長線歷史數據 (日線)
@st.cache_data(ttl=300) 
def get_history_data(symbol, period="6mo"):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period=period)
        return df, stock.info
    except Exception:
        return pd.DataFrame(), {}

# B. 抓今日即時數據 (1分鐘線) - 這是畫出「你截圖那種走勢」的關鍵
@st.cache_data(ttl=60) # 60秒更新一次
def get_intraday_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        # 抓取最近 1 天，頻率為 1 分鐘
        df = stock.history(period="1d", interval="1m")
        return df
    except Exception:
        return pd.DataFrame()

# === 4. 側邊欄：控制中心 ===
st.sidebar.header("🎯 監控標的選擇")
selected_name = st.sidebar.radio("請選擇公司：", list(stock_map.keys()))
ticker = stock_map[selected_name]

# === 5. 頂部佈局：大盤常駐 (Head-Up Display) ===
col_header, col_index = st.columns([3, 1])

with col_header:
    st.title("🏢 遠東集團_聯稽一處戰情指揮中心")
    st.markdown(f"### 目前監控：**{selected_name}**")

with col_index:
    st.markdown("##### 🇹🇼 台灣加權指數")
    index_df, _ = get_history_data("^TWII", period="5d")
    
    if not index_df.empty:
        curr_idx = index_df['Close'].iloc[-1]
        prev_idx = index_df['Close'].iloc[-2]
        chg = curr_idx - prev_idx
        pct = (chg / prev_idx) * 100
        
        st.metric(
            "加權指數", 
            f"{curr_idx:,.0f}", 
            f"{chg:+.0f} ({pct:+.2f}%)",
            delta_color="inverse"
        )
        st.line_chart(index_df['Close'], height=80)

st.markdown("---")

# === 6. 主畫面：數據展示 ===

# 先抓資料
history_df, info = get_history_data(ticker)
intraday_df = get_intraday_data(ticker)

if history_df.empty:
    st.error("⚠️ 無法取得數據，請確認代號或網路連線。")
else:
    # --- A. 關鍵報價看板 ---
    if not intraday_df.empty:
        latest_price = intraday_df['Close'].iloc[-1]
    else:
        latest_price = history_df['Close'].iloc[-1]

    # 計算漲跌
    prev_close = history_df['Close'].iloc[-2] if len(history_df) > 1 else latest_price
    price_change = latest_price - prev_close
    price_pct = (price_change / prev_close) * 100

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("目前股價", f"{latest_price:.1f}", f"{price_change:+.1f} ({price_pct:+.2f}%)", delta_color="inverse")
    with col2:
        st.metric("最高價", f"{history_df['High'].iloc[-1]:.1f}")
    with col3:
        st.metric("最低價", f"{history_df['Low'].iloc[-1]:.1f}")
    with col4:
        vol = history_df['Volume'].iloc[-1] / 1000
        st.metric("成交量 (張)", f"{vol:,.0f}")

    # --- B. ⚡ 今日即時走勢 (重點更新！) ---
    st.subheader("⚡ 今日即時走勢 (1分鐘 K線)")
    
    if not intraday_df.empty:
        # 這裡設定 color=["#FF0000"] 讓線條變成紅色，更有台股上漲的感覺
        st.line_chart(intraday_df['Close'], color=["#FF0000"])
    else:
        st.info("🕒 目前無即時分鐘數據 (可能是盤前或休市中)，請參考下方日線。")

    # --- C. 📅 歷史趨勢 ---
    with st.expander("查看 近半年歷史趨勢 & 月線 (點擊展開)", expanded=True):
        st.subheader("📈 歷史走勢 (半年)")
        history_df['月線 (20MA)'] = history_df['Close'].rolling(window=20).mean()
        # 灰色股價，藍色月線
        st.line_chart(history_df[['Close', '月線 (20MA)']], color=["#AAAAAA", "#0068C9"])

# === 頁尾資訊 (修改處) ===
st.markdown("---")
# 這裡已經改成你的名字了！
st.caption("資料來源：Yahoo Finance | 即時數據更新頻率：60秒 | 開發者：李宗念")
