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

# === ⚠️ CSS 設計師風格注入 (Design System) ===
st.markdown("""
    <style>
        /* 強制全站字體 */
        html, body, [class*="css"] {
            font-family: 'Microsoft JhengHei', '微軟正黑體', sans-serif !important;
        }
        /* 調整 Metric 指標的樣式，讓數字更清楚 */
        div[data-testid="stMetricValue"] {
            font-size: 1.8rem !important; 
            font-weight: 700;
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

# === 3. 數據核心函數 ===

@st.cache_data(ttl=60)
def get_quote_data(symbol):
    """抓取即時報價(用來顯示上面的大數字)"""
    try:
        stock = yf.Ticker(symbol)
        # 這裡為了算漲跌，還是要抓細一點，但我們只取最後一筆
        df_intraday = stock.history(period="1d", interval="1m") 
        df_daily = stock.history(period="5d") 
        return df_intraday, df_daily, stock.info
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), {}

@st.cache_data(ttl=300)
def get_chart_data(symbol, time_range):
    """抓取畫圖用的數據 (根據你的新要求調整)"""
    stock = yf.Ticker(symbol)
    
    if time_range == "⚡ 今日即時 (5分K)":
        # 這裡改成 5 分鐘 K 線
        return stock.history(period="1d", interval="5m")
    elif time_range == "📅 近 5 天 (日K)":
        return stock.history(period="5d", interval="1d")
    elif time_range == "🗓️ 近 1 個月 (日K)":
        return stock.history(period="1mo", interval="1d")
    elif time_range == "📆 近 6 個月 (日K)":
        return stock.history(period="6mo", interval="1d")
    else:
        return stock.history(period="1d", interval="5m")

def calculate_metrics(df_intraday, df_daily, info):
    """計算指標"""
    if df_intraday.empty: return None
    
    current_price = df_intraday['Close'].iloc[-1]
    prev_close = info.get('previousClose')
    if prev_close is None and len(df_daily) >= 2:
        prev_close = df_daily['Close'].iloc[-2]
    if prev_close is None: prev_close = df_intraday['Open'].iloc[0]

    change = current_price - prev_close
    pct_change = (change / prev_close) * 100
    
    # 均價 VWAP 計算
    total_val = (df_intraday['Close'] * df_intraday['Volume']).sum()
    total_vol = df_intraday['Volume'].sum()
    avg_price = total_val / total_vol if total_vol > 0 else current_price

    return {
        "current": current_price, "prev_close": prev_close, "change": change,
        "pct_change": pct_change, "high": df_intraday['High'].max(),
        "low": df_intraday['Low'].min(), "open": df_intraday['Open'].iloc[0],
        "volume": total_vol, "avg_price": avg_price
    }

def draw_mini_chart(df, color):
    """畫右上角大盤的小圖 (含成交量)"""
    if df.empty: return None
    df = df.reset_index()
    
    # 價格線
    line = alt.Chart(df).mark_line(color=color, strokeWidth=2).encode(
        x=alt.X('Datetime:T', axis=None),
        y=alt.Y('Close:Q', scale=alt.Scale(zero=False), axis=None),
        tooltip=['Datetime', 'Close']
    ).properties(height=50) # 高度縮小

    # 成交量 (淡淡的灰色在下面)
    bar = alt.Chart(df).mark_bar(color='#eeeeee').encode(
        x=alt.X('Datetime:T', axis=None),
        y=alt.Y('Volume:Q', axis=None),
        tooltip=['Datetime', 'Volume']
    ).properties(height=30) # 高度更小

    return alt.vconcat(line, bar, spacing=0)

# === 4. 側邊欄 ===
st.sidebar.header("🎯 監控標的選擇")
selected_name = st.sidebar.radio("請選擇公司：", list(stock_map.keys()))
ticker = stock_map[selected_name]
st.sidebar.markdown("---")
st.sidebar.caption(f"✅ 系統連線正常\n👤 開發者：李宗念")

# === 5. 戰情指揮中心佈局 (Dashboard Layout) ===

# 使用 container(border=True) 創造卡片感
with st.container(border=True):
    col_title, col_idx_data, col_idx_chart = st.columns([2, 1, 1.5])
    
    with col_title:
        st.title("🏢 遠東集團戰情中心")
        st.markdown(f"#### 目前監控：**{selected_name}**")
    
    # 抓大盤數據
    idx_intra, idx_daily, idx_info = get_quote_data("^TWII")
    
    with col_idx_data:
        st.markdown("##### 🇹🇼 台灣加權指數")
        if not idx_intra.empty:
            idx_m = calculate_metrics(idx_intra, idx_daily, idx_info)
            st.metric(
                "加權指數", 
                f"{idx_m['current']:,.0f}", 
                f"{idx_m['change']:+.0f} ({idx_m['pct_change']:+.2f}%)",
                delta_color="inverse"
            )
    
    with col_idx_chart:
        if not idx_intra.empty:
            idx_color = '#FF4B4B' if idx_m['change'] >= 0 else '#00C805'
            # 這裡呼叫新的畫圖函數 (含成交量)
            st.altair_chart(draw_mini_chart(idx_intra, idx_color), use_container_width=True)
        else:
            st.warning("大盤連線中...")

# === 6. 主數據區塊 (個股) ===

df_1m, df_1d, info = get_quote_data(ticker)

if df_1m.empty:
    st.error(f"⚠️ 無法取得 {selected_name} 數據。")
else:
    metrics = calculate_metrics(df_1m, df_1d, info)
    
    # 使用另一個 container 包住個股數據，增加層次感
    with st.container(border=True):
        # 第一排數據
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 目前股價", f"{metrics['current']:.2f}", f"{metrics['change']:+.2f} ({metrics['pct_change']:+.2f}%)", delta_color="inverse")
        c2.metric("📊 當日均價 (VWAP)", f"{metrics['avg_price']:.2f}")
        c3.metric("📦 總成交量 (張)", f"{metrics['volume']/1000:,.0f}")
        c4.metric("⚖️ 昨收價", f"{metrics['prev_close']:.2f}")
        
        st.divider() # 分隔線
        
        # 第二排數據
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("🔔 開盤價", f"{metrics['open']:.2f}")
        c6.metric("🔺 最高價", f"{metrics['high']:.2f}")
        c7.metric("🔻 最低價", f"{metrics['low']:.2f}")
        amp = ((metrics['high'] - metrics['low']) / metrics['prev_close']) * 100
        c8.metric("〰️ 當日振幅", f"{amp:.2f}%")

    # === 7. 走勢圖控制區 ===
    st.subheader("📈 股價走勢分析")
    
    # 選單：今日改為 5分K，其他為日K
    time_options = ["⚡ 今日即時 (5分K)", "📅 近 5 天 (日K)", "🗓️ 近 1 個月 (日K)", "📆 近 6 個月 (日K)"]
    selected_time = st.radio("選擇週期：", time_options, horizontal=True)

    chart_df = get_chart_data(ticker, selected_time)

    if not chart_df.empty:
        chart_data = chart_df.reset_index()
        # 處理欄位名稱
        col_name = "Date" if "Date" in chart_data.columns else "Datetime"
        chart_data.rename(columns={col_name: "Time"}, inplace=True)

        # 決定顏色與格式
        if "即時" in selected_time:
            line_color = '#FF4B4B' if metrics['change'] >= 0 else '#00C805'
            time_fmt = '%H:%M'
        else:
            line_color = '#0068C9' # 歷史用藍色
            time_fmt = '%Y-%m-%d'

        # 繪圖
        base = alt.Chart(chart_data).encode(x=alt.X('Time:T', axis=alt.Axis(title='時間', format=time_fmt)))

        # 價格線
        line = base.mark_line(color=line_color).encode(
            y=alt.Y('Close:Q', scale=alt.Scale(zero=False), axis=alt.Axis(title='股價')),
            tooltip=['Time', 'Close', 'Volume']
        ).properties(height=350)

        # 輔助線 (今日畫均價，歷史畫月線)
        if "即時" in selected_time:
             avg_line = alt.Chart(pd.DataFrame({'y': [metrics['avg_price']]})).mark_rule(strokeDash=[5, 5], color='#FFA500').encode(y='y')
             final_chart = line + avg_line
        else:
             chart_data['MA20'] = chart_data['Close'].rolling(window=20).mean()
             ma_line = base.mark_line(color='#FFA500', strokeDash=[5, 5]).encode(y='MA20')
             final_chart = line + ma_line

        # 成交量
        vol = base.mark_bar(color='#cccccc').encode(
            y=alt.Y('Volume:Q', axis=alt.Axis(title='成交量')),
            tooltip=['Time', 'Volume']
        ).properties(height=100)

        combined = alt.vconcat(final_chart, vol).resolve_scale(x='shared')
        st.altair_chart(combined, use_container_width=True)
    else:
        st.info("尚無資料")

# === 頁尾 ===
st.divider()
current_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"""
<div style="text-align: center; color: #888888; font-size: 0.9em;">
    <b>遠東集團_聯稽一處戰情指揮中心</b> | 開發者：<b>李宗念</b><br>
    最後更新：{current_time}
</div>
""", unsafe_allow_html=True)
