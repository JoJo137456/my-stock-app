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

# === ⚠️ CSS 設計師風格注入 (仿 Google Finance) ===
st.markdown("""
    <style>
        /* 強制全站字體 */
        html, body, [class*="css"] {
            font-family: 'Microsoft JhengHei', '微軟正黑體', sans-serif !important;
        }
        /* 調整 Metric 數字大小 */
        div[data-testid="stMetricValue"] {
            font-size: 1.8rem !important; 
            font-weight: 700;
        }
        /* 讓圖表背景更乾淨 */
        canvas {
            border-radius: 10px;
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
    """抓取即時數據"""
    try:
        stock = yf.Ticker(symbol)
        # 抓取 1 分鐘線，這是畫出平滑曲線的關鍵
        df_intraday = stock.history(period="1d", interval="1m") 
        df_daily = stock.history(period="5d") 
        return df_intraday, df_daily, stock.info
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), {}

@st.cache_data(ttl=300)
def get_chart_data(symbol, time_range):
    """抓取歷史圖表數據"""
    stock = yf.Ticker(symbol)
    if "今日" in time_range:
        return stock.history(period="1d", interval="1m")
    elif "5 天" in time_range:
        return stock.history(period="5d", interval="15m") # 5天用15分線比較順
    elif "1 個月" in time_range:
        return stock.history(period="1mo", interval="1d")
    elif "6 個月" in time_range:
        return stock.history(period="6mo", interval="1d")
    else:
        return stock.history(period="1d", interval="1m")

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
    
    # VWAP
    total_val = (df_intraday['Close'] * df_intraday['Volume']).sum()
    total_vol = df_intraday['Volume'].sum()
    avg_price = total_val / total_vol if total_vol > 0 else current_price

    return {
        "current": current_price, "prev_close": prev_close, "change": change,
        "pct_change": pct_change, "high": df_intraday['High'].max(),
        "low": df_intraday['Low'].min(), "open": df_intraday['Open'].iloc[0],
        "volume": total_vol, "avg_price": avg_price
    }

def draw_google_style_chart(df, color, prev_close=None):
    """繪製 Google Finance 風格圖表 (Area Chart + 基準線)"""
    df = df.reset_index()
    # 處理欄位名稱
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)

    # 1. 面積圖 (Area) - 下方的漸層填充
    area = alt.Chart(df).mark_area(
        color=color,
        opacity=0.1,  # 淡淡的顏色
        line=False
    ).encode(
        x=alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M', grid=False)), # X軸不顯示網格
        y=alt.Y('Close:Q', scale=alt.Scale(zero=False), axis=alt.Axis(title='', grid=True, tickCount=5)) # Y軸顯示主要網格
    )

    # 2. 線圖 (Line) - 主走勢
    line = alt.Chart(df).mark_line(
        color=color,
        strokeWidth=2
    ).encode(
        x='Time:T',
        y=alt.Y('Close:Q', scale=alt.Scale(zero=False)),
        tooltip=['Time', 'Close', 'Volume']
    )
    
    # 3. 基準線 (Reference Line) - 昨收價虛線
    if prev_close:
        rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(
            strokeDash=[4, 4], # 虛線樣式
            color='gray',
            opacity=0.6
        ).encode(y='y')
        return (area + line + rule).properties(height=350)
    else:
        return (area + line).properties(height=350)

# === 4. 側邊欄 ===
st.sidebar.header("🎯 監控標的選擇")
selected_name = st.sidebar.radio("請選擇公司：", list(stock_map.keys()))
ticker = stock_map[selected_name]
st.sidebar.markdown("---")
st.sidebar.caption(f"✅ 系統連線正常\n👤 開發者：李宗念")

# === 5. 頂部戰情儀表 (HUD) ===

with st.container(border=True):
    col_title, col_idx_data, col_idx_chart = st.columns([2, 1, 1.5])
    
    with col_title:
        st.title("🏢 遠東集團戰情中心")
        st.markdown(f"#### 目前監控：**{selected_name}**")
    
    # 大盤
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
            idx_color = '#d62728' if idx_m['change'] >= 0 else '#2ca02c' # 台股紅漲綠跌
            # 大盤也用 Google 風格小圖
            idx_chart = draw_google_style_chart(idx_intra, idx_color, idx_m['prev_close'])
            st.altair_chart(idx_chart.properties(height=60), use_container_width=True)

# === 6. 主數據區塊 ===

df_1m, df_1d, info = get_quote_data(ticker)

if df_1m.empty:
    st.error(f"⚠️ 無法取得 {selected_name} 數據。")
else:
    metrics = calculate_metrics(df_1m, df_1d, info)
    
    # 決定顏色 (台股習慣：漲是紅，跌是綠)
    # Google Finance 的邏輯：如果現在價格 > 昨收，整張圖就是紅色；反之綠色
    chart_color = '#d62728' if metrics['change'] >= 0 else '#2ca02c' 

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 目前股價", f"{metrics['current']:.2f}", f"{metrics['change']:+.2f} ({metrics['pct_change']:+.2f}%)", delta_color="inverse")
        c2.metric("📊 當日均價", f"{metrics['avg_price']:.2f}")
        c3.metric("📦 總成交量", f"{metrics['volume']/1000:,.0f} 張")
        c4.metric("⚖️ 昨收價", f"{metrics['prev_close']:.2f}")
        
        st.divider()
        
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("🔔 開盤價", f"{metrics['open']:.2f}")
        c6.metric("🔺 最高價", f"{metrics['high']:.2f}")
        c7.metric("🔻 最低價", f"{metrics['low']:.2f}")
        amp = ((metrics['high'] - metrics['low']) / metrics['prev_close']) * 100
        c8.metric("〰️ 當日振幅", f"{amp:.2f}%")

    # === 7. Google Style 走勢圖 ===
    st.subheader("📈 股價走勢")
    
    # 時間選單
    time_options = ["⚡ 今日即時", "📅 近 5 天", "🗓️ 近 1 個月", "📆 近 6 個月"]
    selected_time = st.radio("區間：", time_options, horizontal=True, label_visibility="collapsed")

    chart_df = get_chart_data(ticker, selected_time)

    if not chart_df.empty:
        # 如果是「今日」，一定要畫昨收基準線
        ref_price = metrics['prev_close'] if "今日" in selected_time else None
        
        # 繪圖
        final_chart = draw_google_style_chart(chart_df, chart_color, ref_price)
        st.altair_chart(final_chart, use_container_width=True)
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
