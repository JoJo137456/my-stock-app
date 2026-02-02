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

# === 3. 數據核心函數 ===

@st.cache_data(ttl=30) # 縮短快取時間以確保數據新鮮
def get_data(symbol):
    """
    抓取數據邏輯：
    1. info: 用來拿最準確的「昨收」和「現價」(收盤後這最準)
    2. history(1m): 用來畫走勢圖
    """
    try:
        stock = yf.Ticker(symbol)
        # 1. 抓走勢圖用的分鐘資料
        df_intraday = stock.history(period="1d", interval="1m")
        
        # 2. 抓官方資訊 (收盤後這個最準)
        info = stock.info
        
        return df_intraday, info
    except Exception:
        return pd.DataFrame(), {}

def calculate_metrics(df, info):
    """
    計算指標：優先使用官方 info，若無則從 dataframe 推算
    """
    if df.empty: return None
    
    # --- 關鍵修正：優先使用 info 的數據 ---
    # 昨收價 (Previous Close)
    prev_close = info.get('previousClose')
    if prev_close is None:
        # 如果真的沒有，才用第一筆開盤價充當
        prev_close = df['Open'].iloc[0]

    # 目前股價 (Current Price)
    # 收盤後 info['currentPrice'] 通常是最後定價，比 1m 線的最後一筆準
    current_price = info.get('currentPrice')
    if current_price is None:
        current_price = df['Close'].iloc[-1]

    # 計算漲跌
    change = current_price - prev_close
    pct_change = (change / prev_close) * 100
    
    # 其他統計數據 (這些從分鐘線算沒問題)
    high = df['High'].max()
    low = df['Low'].min()
    open_price = df['Open'].iloc[0]
    volume = df['Volume'].sum()
    
    # VWAP (當日均價)
    total_val = (df['Close'] * df['Volume']).sum()
    total_vol = df['Volume'].sum()
    avg_price = total_val / total_vol if total_vol > 0 else current_price

    return {
        "current": current_price, "prev_close": prev_close, "change": change,
        "pct_change": pct_change, "high": high, "low": low,
        "open": open_price, "volume": volume, "avg_price": avg_price
    }

def draw_dynamic_chart(df, color, prev_close):
    """
    繪製動態縮放圖表 (解決躺平問題)
    """
    df = df.reset_index()
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)

    # === 關鍵算法：計算 Y 軸範圍 ===
    # 找出數據中的最大值與最小值
    y_min = df['Close'].min()
    y_max = df['Close'].max()
    
    # 如果波動太小 (例如整天只有一個價格)，強制給一點緩衝，不然圖會壞掉
    if y_max == y_min:
        buffer = 0.1
    else:
        # 上下各留 10% 空間，讓線條不要頂到天花板
        buffer = (y_max - y_min) * 0.1
    
    # 設定顯示範圍 (Domain)
    y_domain = [y_min - buffer, y_max + buffer]

    # 1. 面積圖 (背景)
    area = alt.Chart(df).mark_area(
        color=color, opacity=0.1, line=False
    ).encode(
        x=alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M', grid=False)),
        y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain), axis=alt.Axis(title='', grid=True))
    )

    # 2. 線圖 (主走勢) - 注意這裡也套用了 domain
    line = alt.Chart(df).mark_line(
        color=color, strokeWidth=2
    ).encode(
        x='Time:T',
        y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain)),
        tooltip=['Time', 'Close', 'Volume']
    )
    
    # 3. 昨收基準線 (虛線)
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(
        strokeDash=[4, 4], color='gray', opacity=0.5
    ).encode(y='y')

    return (area + line + rule).properties(height=350)

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
    
    # 大盤數據
    idx_df, idx_info = get_data("^TWII")
    
    with col_idx_data:
        st.markdown("##### 🇹🇼 台灣加權指數")
        if not idx_df.empty:
            idx_m = calculate_metrics(idx_df, idx_info)
            if idx_m:
                st.metric(
                    "加權指數", 
                    f"{idx_m['current']:,.0f}", 
                    f"{idx_m['change']:+.0f} ({idx_m['pct_change']:+.2f}%)",
                    delta_color="inverse"
                )
    
    with col_idx_chart:
        if not idx_df.empty and idx_m:
            idx_color = '#d62728' if idx_m['change'] >= 0 else '#2ca02c'
            # 大盤小圖也套用動態縮放
            st.altair_chart(
                draw_dynamic_chart(idx_df, idx_color, idx_m['prev_close']).properties(height=60), 
                use_container_width=True
            )

# === 6. 主數據區塊 ===

df_stock, stock_info = get_data(ticker)

if df_stock.empty:
    st.error(f"⚠️ 無法取得 {selected_name} 數據。")
else:
    metrics = calculate_metrics(df_stock, stock_info)
    
    # 顏色邏輯
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

    # === 7. Google Style 動態縮放走勢圖 ===
    st.subheader("📈 今日即時走勢 (1分K)")
    
    # 這裡呼叫新的 draw_dynamic_chart 函數
    final_chart = draw_dynamic_chart(df_stock, chart_color, metrics['prev_close'])
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
