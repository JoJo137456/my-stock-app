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

# === ⚠️ CSS 優化：微軟正黑體 + 數據字體放大 ===
st.markdown("""
    <style>
        html, body, [class*="css"] {
            font-family: 'Microsoft JhengHei', '微軟正黑體', sans-serif !important;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.6rem !important; 
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

@st.cache_data(ttl=30)
def get_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        # 1. 抓取今日分鐘線 (畫圖、算即時均價用)
        df_intraday = stock.history(period="1d", interval="1m")
        
        # 2. 抓取官方 Info (拿昨收、總成交量、總市值等結算數據)
        info = stock.info
        
        return df_intraday, info
    except Exception:
        return pd.DataFrame(), {}

def calculate_metrics(df, info):
    if df.empty: return None
    
    # --- A. 價格與漲跌 (優先信任 Info，若無則用分鐘線推算) ---
    
    # 1. 昨收價
    prev_close = info.get('previousClose')
    if prev_close is None: prev_close = df['Open'].iloc[0] # 防呆

    # 2. 目前股價 (收盤後 info['currentPrice'] 最準)
    current_price = info.get('currentPrice')
    if current_price is None: current_price = df['Close'].iloc[-1]

    # 3. 漲跌價差 (User 要求：要看到多少元)
    change_amount = current_price - prev_close
    change_pct = (change_amount / prev_close) * 100

    # --- B. 成交量與金額 (User 要求：成交量要準，要有成交金額) ---
    
    # 1. 總成交量 (優先抓 info['volume']，這是整日結算值)
    total_volume_shares = info.get('volume')
    # 如果 info 沒更新 (盤中常見)，改用分鐘線加總
    if total_volume_shares is None or total_volume_shares == 0:
        total_volume_shares = df['Volume'].sum()
    
    # 2. 成交金額 (Turnover) - 估算值
    # 因為 info 通常不給台股成交金額，我們用 分鐘線 Price * Volume 加總
    # 這會比實際值略低一點點 (因為沒算到盤後定價)，但已是最接近的
    turnover_est = (df['Close'] * df['Volume']).sum()

    # --- C. 均價 (VWAP) ---
    # 公式：總成交金額 / 總成交股數
    avg_price = turnover_est / total_volume_shares if total_volume_shares > 0 else current_price

    return {
        "current": current_price,
        "prev_close": prev_close,
        "change_amount": change_amount, # 漲跌金額
        "change_pct": change_pct,       # 漲跌趴數
        "high": df['High'].max(),
        "low": df['Low'].min(),
        "open": df['Open'].iloc[0],
        "volume_lots": total_volume_shares / 1000, # 換算成「張」
        "turnover_亿": turnover_est / 100000000,   # 換算成「億」
        "avg_price": avg_price
    }

def draw_dynamic_chart(df, color, prev_close):
    """
    繪製動態縮放圖表 (強制放大波動)
    """
    df = df.reset_index()
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)

    # === 關鍵：Y 軸範圍計算 (解決一直線問題) ===
    y_min = df['Close'].min()
    y_max = df['Close'].max()
    
    # 計算波動幅度
    diff = y_max - y_min
    
    # 如果波動極小 (例如只動 0.05)，我們強制給一個非常小的緩衝，讓線條看起來有動
    # 之前給 10% 太大，現在改給 0.05 或 5% 取小值，逼近線條
    if diff == 0:
        buffer = 0.05
    else:
        buffer = diff * 0.05 # 只留 5% 邊界
    
    y_domain = [y_min - buffer, y_max + buffer]

    # 1. 面積圖
    area = alt.Chart(df).mark_area(
        color=color, opacity=0.1, line=False
    ).encode(
        x=alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M', grid=False)),
        y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain), axis=alt.Axis(title='', grid=True))
    )

    # 2. 線圖
    line = alt.Chart(df).mark_line(
        color=color, strokeWidth=2
    ).encode(
        x='Time:T',
        y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain)),
        tooltip=['Time', 'Close', 'Volume']
    )
    
    # 3. 昨收基準線
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
                    f"{idx_m['change_amount']:+.0f} ({idx_m['change_pct']:+.2f}%)", # 補上漲跌點數
                    delta_color="inverse"
                )
    
    with col_idx_chart:
        if not idx_df.empty and idx_m:
            idx_color = '#d62728' if idx_m['change_amount'] >= 0 else '#2ca02c'
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
    chart_color = '#d62728' if metrics['change_amount'] >= 0 else '#2ca02c' 

    with st.container(border=True):
        # 第一排：核心價格數據
        c1, c2, c3, c4 = st.columns(4)
        
        # 1. 目前股價 + 漲跌金額 (User 要求)
        c1.metric(
            "💰 目前股價", 
            f"{metrics['current']:.2f}", 
            f"{metrics['change_amount']:+.2f} ({metrics['change_pct']:+.2f}%)", 
            delta_color="inverse"
        )
        
        # 2. 當日均價
        c2.metric("📊 當日均價 (VWAP)", f"{metrics['avg_price']:.2f}")
        
        # 3. 總成交量 (修正後數據)
        c3.metric("📦 總成交量", f"{metrics['volume_lots']:,.0f} 張")
        
        # 4. 成交金額 (新功能)
        c4.metric("💎 成交金額", f"{metrics['turnover_亿']:.2f} 億")
        
        st.divider()
        
        # 第二排：OHLC 數據
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("🔔 開盤價", f"{metrics['open']:.2f}")
        c6.metric("🔺 最高價", f"{metrics['high']:.2f}")
        c7.metric("🔻 最低價", f"{metrics['low']:.2f}")
        c8.metric("⚖️ 昨收價", f"{metrics['prev_close']:.2f}")

    # === 7. Google Style 走勢圖 ===
    st.subheader("📈 今日即時走勢 (1分K)")
    
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
