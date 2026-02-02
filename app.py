import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# === 1. 網頁基本設定 (設定標題與寬版模式) ===
st.set_page_config(page_title="遠東集團戰情中心", layout="wide")

# === 2. 定義遠東集團關注清單 (名稱對應代號) ===
# 博弘(6997)為興櫃或新股，若抓不到數據屬正常現象(Yahoo Finance限制)
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

# === 3. 抓取數據函數 (包含快取以提升速度) ===
@st.cache_data(ttl=60) # 設定 60秒快取，避免頻繁請求
def get_stock_data(symbol, period="1mo"):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period=period)
        info = stock.info
        return df, info
    except Exception:
        return pd.DataFrame(), {}

# === 4. 側邊欄：控制中心 ===
st.sidebar.header("🎯 監控標的選擇")
selected_name = st.sidebar.radio("請選擇公司：", list(stock_map.keys()))
ticker = stock_map[selected_name]

# === 5. 頂部佈局：左邊標題，右邊大盤 (Top Bar) ===
# 使用 3:1 的比例，左邊放標題，右邊放台灣大盤指數
col_header, col_index = st.columns([3, 1])

with col_header:
    st.title("🏢 遠東集團_聯稽一處戰情指揮中心")
    st.markdown(f"### 目前監控：**{selected_name}**")

with col_index:
    # 抓取台灣加權指數 (^TWII)
    st.markdown("##### 🇹🇼 台灣加權指數")
    index_df, index_info = get_stock_data("^TWII", period="5d") # 抓5天畫小圖
    
    if not index_df.empty:
        # 計算大盤漲跌
        current_index = index_df['Close'].iloc[-1]
        prev_index = index_df['Close'].iloc[-2]
        change = current_index - prev_index
        pct_change = (change / prev_index) * 100
        
        # 顯示大盤數據 (綠色漲，紅色跌 - Streamlit 預設綠漲紅跌，若要台股習慣需反過來想)
        # 這裡用 delta_color="inverse" 讓紅色代表漲，綠色代表跌 (符合台股習慣)
        st.metric(
            label="加權指數",
            value=f"{current_index:,.0f}",
            delta=f"{change:+.0f} ({pct_change:+.2f}%)",
            delta_color="inverse" 
        )
        # 畫一個迷你的大盤走勢圖
        st.line_chart(index_df['Close'], height=100)
    else:
        st.warning("大盤數據連線中...")

st.markdown("---") # 分隔線

# === 6. 主畫面：個股詳細數據 ===
try:
    # 抓取個股數據 (預設抓 6 個月，看趨勢)
    df, info = get_stock_data(ticker, period="6mo")

    if df.empty:
        st.error(f"⚠️ 無法取得 {selected_name} 的數據，可能是剛開盤或代號有誤。")
    else:
        # --- A. 個股即時報價看板 ---
        latest_price = df['Close'].iloc[-1]
        prev_close = df['Close'].iloc[-2] if len(df) > 1 else latest_price
        price_change = latest_price - prev_close
        price_pct = (price_change / prev_close) * 100

        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="目前股價 (TWD)",
                value=f"{latest_price:.1f}",
                delta=f"{price_change:+.1f} ({price_pct:+.2f}%)",
                delta_color="inverse" # 台股習慣：紅漲綠跌
            )
        with col2:
            st.metric(label="最高價", value=f"{df['High'].iloc[-1]:.1f}")
        with col3:
            st.metric(label="最低價", value=f"{df['Low'].iloc[-1]:.1f}")
        with col4:
            # 成交量換算成「張」
            vol_in_lot = df['Volume'].iloc[-1] / 1000 
            st.metric(label="成交量 (張)", value=f"{vol_in_lot:,.0f}")

        # --- B. 股價走勢圖 (Line Chart) ---
        st.subheader("📈 股價走勢 (近半年)")
        # 加上 20日均線 (月線)
        df['月線 (20MA)'] = df['Close'].rolling(window=20).mean()
        
        st.line_chart(df[['Close', '月線 (20MA)']], color=["#FF4B4B", "#0068C9"])

        # --- C. 成交量圖 (Bar Chart) ---
        st.subheader("📊 成交量變化")
        st.bar_chart(df['Volume'])

except Exception as e:
    st.error(f"發生未預期的錯誤: {e}")

# === 頁尾資訊 ===
st.markdown("---")
st.caption("資料來源：Yahoo Finance (延遲報價約 20 分鐘) | 開發者：聯稽一處戰情官")
