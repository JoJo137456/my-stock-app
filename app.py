import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import pytz

# 設定台灣時區
tw_tz = pytz.timezone('Asia/Taipei')

# === 1. 網頁基本設定 ===
st.set_page_config(page_title="遠東集團戰情中心", layout="wide")

# === ⚠️ CSS 全站字體優化 ===
st.markdown("""
    <style>
        html, body, [class*="css"] {
            font-family: 'Microsoft JhengHei', '微軟正黑體', sans-serif !important;
        }
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

# === 3. 數據核心函數 (修正版) ===

@st.cache_data(ttl=60)
def get_quote_data(symbol):
    """
    抓取數據的核心邏輯：
    為了確保漲跌幅計算正確，我們必須自己算 'Prev Close'，不能依賴 info
    """
    try:
        stock = yf.Ticker(symbol)
        
        # 1. 抓取今日即時 (1分K) -> 用來看現在價格
        df_intraday = stock.history(period="1d", interval="1m")
        
        # 2. 抓取過去 5 天日線 -> 用來找昨收
        df_daily = stock.history(period="5d", interval="1d")
        
        return df_intraday, df_daily
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

def calculate_metrics(df_intraday, df_daily):
    """
    精密計算指標函數
    """
    if df_intraday.empty: return None
    
    # === A. 取得目前價格 ===
    current_price = df_intraday['Close'].iloc[-1]
    current_date = df_intraday.index[-1].date()
    
    # === B. 尋找正確的「昨收價」 ===
    # 邏輯：從日線資料中，找到日期比「今天」小的那一筆，就是昨收
    # 這樣可以避免 yfinance 資料包含今日日線導致抓錯
    
    # 先把日線 index 轉成 date 物件方便比較
    df_daily_clean = df_daily.copy()
    df_daily_clean['DateObj'] = df_daily_clean.index.date
    
    # 篩選出日期小於今天的資料
    past_data = df_daily_clean[df_daily_clean['DateObj'] < current_date]
    
    if not past_data.empty:
        prev_close = past_data['Close'].iloc[-1]
    else:
        # 萬一真的抓不到 (例如週一剛開盤資料延遲)，用今日開盤價暫代防錯
        prev_close = df_intraday['Open'].iloc[0]

    # === C. 計算漲跌 ===
    change = current_price - prev_close
    pct_change = (change / prev_close) * 100
    
    # === D. 其他數據 ===
    high = df_intraday['High'].max()
    low = df_intraday['Low'].min()
    open_price = df_intraday['Open'].iloc[0]
    volume = df_intraday['Volume'].sum()
    
    # VWAP (當日均價)
    total_val = (df_intraday['Close'] * df_intraday['Volume']).sum()
    total_vol = df_intraday['Volume'].sum()
    avg_price = total_val / total_vol if total_vol > 0 else current_price

    return {
        "current": current_price, "prev_close": prev_close, "change": change,
        "pct_change": pct_change, "high": high, "low": low,
        "open": open_price, "volume": volume, "avg_price": avg_price
    }

def draw_google_style_chart(df, color, prev_close):
    """繪製 1分K 的 Google 風格圖表"""
    df = df.reset_index()
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)

    # 1. 面積圖 (背景色)
    area = alt.Chart(df).mark_area(
        color=color, opacity=0.1, line=False
    ).encode(
        x=alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M', grid=False)),
        y=alt.Y('Close:Q', scale=alt.Scale(zero=False), axis=alt.Axis(title='', grid=True))
    )

    # 2. 線圖 (主走勢)
    line = alt.Chart(df).mark_line(
        color=color, strokeWidth=2
    ).encode(
        x='Time:T',
        y=alt.Y('Close:Q', scale=alt.Scale(zero=False)),
        tooltip=['Time', 'Close', 'Volume']
    )
    
    # 3. 昨收基準線 (虛線)
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(
        strokeDash=[4, 4], color='gray', opacity=0.6
    ).encode(y='y')

    return (area + line + rule).properties(height=300) # 高度調整

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
    
    # --- 大盤數據處理 ---
    idx_intra, idx_daily = get_quote_data("^TWII")
    
    with col_idx_data:
        st.markdown("##### 🇹🇼 台灣加權指數")
        if not idx_intra.empty:
            # 使用修正後的計算邏輯
            idx_m = calculate_metrics(idx_intra, idx_daily)
            st.metric(
                "加權指數", 
                f"{idx_m['current']:,.0f}", 
                f"{idx_m['change']:+.0f} ({idx_m['pct_change']:+.2f}%)",
                delta_color="inverse"
            )
    
    with col_idx_chart:
        if not idx_intra.empty:
            idx_color = '#d62728' if idx_m['change'] >= 0 else '#2ca02c'
            # 大盤也用 1分K 畫圖
            st.altair_chart(
                draw_google_style_chart(idx_intra, idx_color, idx_m['prev_close']).properties(height=60), 
                use_container_width=True
            )

# === 6. 主數據區塊 (個股) ===

df_1m, df_daily = get_quote_data(ticker)

if df_1m.empty:
    st.error(f"⚠️ 無法取得 {selected_name} 數據。")
else:
    # 計算個股指標
    metrics = calculate_metrics(df_1m, df_daily)
    
    # 決定顏色 (紅漲綠跌)
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

    # === 7. 走勢圖 (1分K Google Style) ===
    st.subheader("📈 今日即時走勢 (1分K)")
    
    # 這裡直接畫圖，因為我們就是要看 1分K
    final_chart = draw_google_style_chart(df_1m, chart_color, metrics['prev_close'])
    st.altair_chart(final_chart, use_container_width=True)

# === 頁尾 ===
st.divider()
current_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"""
<div style="text-align: center; color: #888888; font-size: 0.9em;">
    <b>遠東集團_聯稽一處戰情指揮中心</b> | 開發者：<b>李宗念</b><br>
    最後更新：{current_time}
</div>
""", unsafe_allow_html=True)
