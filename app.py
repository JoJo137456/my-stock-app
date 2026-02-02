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

# === ⚠️ CSS 優化：微軟正黑體 + 數據字體放大 + 去除圖表留白 ===
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
@st.cache_data(ttl=30)  # 設定快取 30 秒更新一次
def get_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        # 1. 抓取今日分鐘線
        df_intraday = stock.history(period="1d", interval="1m")
        
        # 2. 抓取 Info
        info = stock.info
        
        return df_intraday, info
    except Exception:
        return pd.DataFrame(), {}

def calculate_metrics(df, info):
    if df.empty: return None
    
    # --- A. 價格處理 ---
    # 優先使用 Info 的昨收，如果沒有則用今日第一筆 Open 代替 (防呆)
    prev_close = info.get('previousClose')
    if prev_close is None: 
        prev_close = df['Open'].iloc[0]

    # 目前價格：優先用 Info 的 currentPrice (即時性較高)，如果沒有則用 DataFrame 最後一筆
    current_price = info.get('currentPrice')
    if current_price is None or current_price == 0:
        current_price = df['Close'].iloc[-1]

    # 漲跌計算
    change_amount = current_price - prev_close
    change_pct = (change_amount / prev_close) * 100

    # --- B. 成交量與金額優化 (解決勾稽問題) ---
    # 1. 總成交量：info['volume'] 通常是總量，但盤中可能延遲。
    # 如果 info 的量小於 df 加總，我們信任 df (因為 df 是累計的)
    df_vol_sum = df['Volume'].sum()
    info_vol = info.get('volume', 0)
    
    total_volume_shares = max(df_vol_sum, info_vol) if info_vol is not None else df_vol_sum

    # 2. 成交金額 (Turnover) 精確化算法
    # 舊算法：Close * Volume (誤差大)
    # 新算法：(High + Low + Close) / 3 * Volume (誤差較小，稱為典型價格)
    df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
    turnover_est = (df['Typical_Price'] * df['Volume']).sum()

    # --- C. 均價 (VWAP) ---
    avg_price = turnover_est / total_volume_shares if total_volume_shares > 0 else current_price

    return {
        "current": current_price,
        "prev_close": prev_close,
        "change_amount": change_amount,
        "change_pct": change_pct,
        "high": df['High'].max(),
        "low": df['Low'].min(),
        "open": df['Open'].iloc[0],
        "volume_lots": total_volume_shares / 1000,   # 張數
        "turnover_亿": turnover_est / 100000000,     # 億元
        "avg_price": avg_price
    }

def draw_dynamic_chart(df, color, prev_close):
    """
    修正版：強制 Y 軸不包含 0，並動態計算邊界，解決一直線問題
    """
    df = df.reset_index()
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)
    
    # 確保時間欄位是 datetime 格式
    df['Time'] = pd.to_datetime(df['Time']).dt.tz_convert(tw_tz)

    y_min = df['Close'].min()
    y_max = df['Close'].max()
    
    # 邏輯修正：如果波動極小（例如定存股或盤整），Altair 預設會把圖壓扁
    # 我們手動計算一個 domain，讓它上下至少保留 0.2% 的空間
    span = y_max - y_min
    if span == 0:
        span = prev_close * 0.005 # 如果完全沒動，給 0.5% 緩衝
    
    padding = span * 0.2 # 上下各留 20% 緩衝
    y_domain = [y_min - padding, y_max + padding]

    # 1. 面積圖
    area = alt.Chart(df).mark_area(
        color=color, opacity=0.1, line=False
    ).encode(
        x=alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M', grid=False)),
        y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain, zero=False), axis=alt.Axis(title='', grid=True))
    )

    # 2. 線圖
    line = alt.Chart(df).mark_line(
        color=color, strokeWidth=2
    ).encode(
        x='Time:T',
        y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain, zero=False)), # 關鍵：zero=False
        tooltip=[
            alt.Tooltip('Time', title='時間', format='%H:%M'),
            alt.Tooltip('Close', title='價格', format=',.2f'),
            alt.Tooltip('Volume', title='量', format=',.0f')
        ]
    )
    
    # 3. 昨收基準線
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(
        strokeDash=[4, 4], color='gray', opacity=0.5
    ).encode(y='y')

    return (area + line + rule).properties(height=250) # 高度設為 250 看起來比較舒適

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
    
    if not idx_df.empty:
        idx_m = calculate_metrics(idx_df, idx_info)
        
        with col_idx_data:
            st.markdown("##### 🇹🇼 台灣加權指數")
            if idx_m:
                st.metric(
                    "加權指數",
                    f"{idx_m['current']:,.0f}",
                    f"{idx_m['change_amount']:+.0f} ({idx_m['change_pct']:+.2f}%)",
                    delta_color="inverse"
                )
        
        with col_idx_chart:
            if idx_m:
                idx_color = '#d62728' if idx_m['change_amount'] >= 0 else '#2ca02c'
                # 這裡調用圖表函數
                st.altair_chart(
                    draw_dynamic_chart(idx_df, idx_color, idx_m['prev_close']).properties(height=80), 
                    use_container_width=True
                )

# === 6. 主數據區塊 ===
df_stock, stock_info = get_data(ticker)

if df_stock.empty:
    st.error(f"⚠️ 無法取得 {selected_name} 數據，請稍後再試。")
else:
    metrics = calculate_metrics(df_stock, stock_info)
    
    if metrics:
        chart_color = '#d62728' if metrics['change_amount'] >= 0 else '#2ca02c'
        
        with st.container(border=True):
            # 第一排：核心價格數據
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💰 目前股價", f"{metrics['current']:.2f}", f"{metrics['change_amount']:+.2f} ({metrics['change_pct']:+.2f}%)", delta_color="inverse")
            c2.metric("📊 當日均價 (VWAP)", f"{metrics['avg_price']:.2f}")
            c3.metric("📦 總成交量", f"{metrics['volume_lots']:,.0f} 張")
            c4.metric("💎 成交金額 (估)", f"{metrics['turnover_亿']:.2f} 億")
            
            st.divider()
            
            # 第二排：OHLC 數據
            c5, c6, c7, c8 = st.columns(4)
            c5.metric("🔔 開盤價", f"{metrics['open']:.2f}")
            c6.metric("🔺 最高價", f"{metrics['high']:.2f}")
            c7.metric("🔻 最低價", f"{metrics['low']:.2f}")
            c8.metric("⚖️ 昨收價", f"{metrics['prev_close']:.2f}")

        # === 7. Google Style 走勢圖 ===
        st.subheader("📈 今日即時走勢")
        final_chart = draw_dynamic_chart(df_stock, chart_color, metrics['prev_close'])
        st.altair_chart(final_chart, use_container_width=True)

# === 頁尾 ===
st.divider()
current_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"""
<div style="text-align: center; color: #888888; font-size: 0.9em;">
    &nbsp;&nbsp;&nbsp;&nbsp;<b>遠東集團_聯稽一處戰情指揮中心</b> | 開發者：<b>李宗念</b><br>
    &nbsp;&nbsp;&nbsp;&nbsp;最後更新：{current_time}
</div>
""", unsafe_allow_html=True)
