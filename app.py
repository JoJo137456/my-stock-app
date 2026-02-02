import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime
import pytz

# === 1. 系統初始化 ===
st.set_page_config(page_title="遠東集團戰情中心", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

# 強制 CSS：微軟正黑體 + 數字放大 + 移除圖表留白
st.markdown("""
    <style>
        html, body, [class*="css"] {
            font-family: 'Microsoft JhengHei', '微軟正黑體', sans-serif !important;
        }
        div[data-testid="stMetricValue"] {
            font-size: 2rem !important;
            font-weight: 700;
        }
        /* 讓圖表更緊湊 */
        canvas {
            border-radius: 0px !important;
        }
    </style>
""", unsafe_allow_html=True)

# === 2. 監控清單 ===
stock_map = {
    "1402 遠東新": "1402.TW",
    "1102 亞泥": "1102.TW",
    "2606 裕民": "2606.TW",
    "1460 宏遠": "1460.TW",
    "2903 遠百": "2903.TW",
    "4904 遠傳": "4904.TW",
    "1710 東聯": "1710.TW"
}

# === 3. 核心數據引擎 (雙軌制) ===

@st.cache_data(ttl=10) # 極短快取，確保即時
def get_clean_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        
        # 軌道一：抓「日線」 (Daily) -> 為了拿最準確的總量、昨收、高低
        df_daily = stock.history(period="5d", interval="1d")
        
        # 軌道二：抓「分鐘線」 (Intraday) -> 純粹為了畫走勢圖
        df_minute = stock.history(period="1d", interval="1m")
        
        return df_daily, df_minute
    except:
        return pd.DataFrame(), pd.DataFrame()

def calculate_precise_metrics(df_daily, df_minute):
    """
    數據清洗與計算中心
    """
    if df_daily.empty or df_minute.empty: return None

    # 1. 取得今日數據 (日線的最後一筆)
    today_data = df_daily.iloc[-1]
    
    # 2. 取得昨日數據 (日線的倒數第二筆)
    # 邏輯：如果現在是盤中，iloc[-1] 是今天，iloc[-2] 是昨天
    if len(df_daily) >= 2:
        prev_data = df_daily.iloc[-2]
        prev_close = prev_data['Close']
    else:
        prev_close = df_minute['Open'].iloc[0] # 防呆

    # 3. 價格處理
    # 收盤後用日線 Close，盤中用分鐘線最後一筆 Close (因為日線盤中更新慢)
    current_price = df_minute['Close'].iloc[-1]
    
    # 4. 漲跌計算
    change = current_price - prev_close
    pct_change = (change / prev_close) * 100
    
    # 5. 成交量處理 (Volume)
    # yfinance 的分鐘線加總常漏失，直接拿日線的 Volume 最準
    total_volume = today_data['Volume']
    
    # 萬一盤中日線 Volume 還沒更新 (有時會發生)，退回用分鐘線加總
    if total_volume == 0:
        total_volume = df_minute['Volume'].sum()

    # 6. 成交金額估算 (Turnover)
    # 算法：今日成交總量 * VWAP (分鐘線成交量加權平均價)
    vwap_num = (df_minute['Close'] * df_minute['Volume']).sum()
    vwap_den = df_minute['Volume'].sum()
    avg_price = vwap_num / vwap_den if vwap_den > 0 else current_price
    
    turnover_est = total_volume * avg_price # 估算總成交金額

    return {
        "current": current_price,
        "prev_close": prev_close,
        "change": change,
        "pct_change": pct_change,
        "high": df_minute['High'].max(), # 用分鐘線找高低點比較即時
        "low": df_minute['Low'].min(),
        "open": df_minute['Open'].iloc[0],
        "volume": total_volume,
        "amount_e": turnover_est / 100000000, # 換算億
        "avg_price": avg_price
    }

def draw_combo_chart(df, color, prev_close):
    """
    繪製 價格(上) + 成交量(下) 的組合圖
    """
    df = df.reset_index()
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)

    # === 強制撐開 Y 軸邏輯 ===
    y_min = df['Close'].min()
    y_max = df['Close'].max()
    diff = y_max - y_min
    
    # 如果波動極小 (例如只動 0.05)，強制給極小的緩衝 (0.05)
    # 這樣線條就會有起伏，不會變成死魚線
    buffer = 0.05 if diff < 0.1 else diff * 0.1
    y_domain = [y_min - buffer, y_max + buffer]

    # 設定 X 軸 (共用)
    x_axis = alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M', grid=False))

    # --- 上圖：價格走勢 (面積 + 線 + 基準線) ---
    # 1. 背景漸層面積
    area = alt.Chart(df).mark_area(
        color=color, opacity=0.1, line=False
    ).encode(
        x=x_axis,
        y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain), axis=alt.Axis(title='股價', grid=True))
    )
    
    # 2. 主線條
    line = alt.Chart(df).mark_line(
        color=color, strokeWidth=2
    ).encode(
        x=x_axis,
        y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain)),
        tooltip=['Time', 'Close', 'Volume']
    )
    
    # 3. 昨收虛線
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(
        strokeDash=[4, 4], color='gray', opacity=0.8
    ).encode(y='y')
    
    price_chart = (area + line + rule).properties(height=300)

    # --- 下圖：成交量 (柱狀) ---
    vol_chart = alt.Chart(df).mark_bar(
        color=color, opacity=0.5 # 顏色跟著漲跌變
    ).encode(
        x=alt.X('Time:T', axis=None), # 不顯示時間文字，對齊上方
        y=alt.Y('Volume:Q', axis=alt.Axis(title='成交量', tickCount=3)),
        tooltip=['Time', 'Volume']
    ).properties(height=80) # 高度較矮

    # 組合
    return alt.vconcat(price_chart, vol_chart, spacing=0).resolve_scale(x='shared')

# === 4. 側邊欄 ===
st.sidebar.header("🎯 監控標的選擇")
selected_name = st.sidebar.radio("請選擇公司：", list(stock_map.keys()))
ticker = stock_map[selected_name]
st.sidebar.markdown("---")
st.sidebar.caption(f"✅ 系統連線正常 | 開發者：李宗念")

# === 5. 戰情儀表板 ===

# 容器排版
with st.container(border=True):
    col_head, col_idx = st.columns([2, 1])
    with col_head:
        st.title("🏢 遠東集團戰情中心")
        st.markdown(f"### 🔥 目前監控：**{selected_name}**")
    
    # 大盤 Mini Chart
    idx_daily, idx_min = get_clean_data("^TWII")
    with col_idx:
        if not idx_min.empty:
            idx_m = calculate_precise_metrics(idx_daily, idx_min)
            if idx_m:
                idx_color = '#d62728' if idx_m['change'] >= 0 else '#2ca02c'
                st.metric("🇹🇼 加權指數", f"{idx_m['current']:,.0f}", f"{idx_m['change']:+.0f} ({idx_m['pct_change']:+.2f}%)", delta_color="inverse")

# === 6. 個股數據與圖表 ===

df_d, df_m = get_clean_data(ticker)

if df_m.empty:
    st.error("⚠️ 資料讀取失敗，可能是盤後資料整理中，請稍後重整。")
else:
    m = calculate_precise_metrics(df_d, df_m)
    
    # 顏色邏輯：台股 紅漲 綠跌
    main_color = '#d62728' if m['change'] >= 0 else '#2ca02c'

    # --- 數據卡片 ---
    with st.container(border=True):
        # 第一排
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 目前股價", f"{m['current']:.2f}", f"{m['change']:+.2f} ({m['pct_change']:+.2f}%)", delta_color="inverse")
        c2.metric("💎 成交金額 (估)", f"{m['amount_e']:.2f} 億") # 這是你要的
        c3.metric("📦 總成交量", f"{m['volume']/1000:,.0f} 張") # 這是你要的
        c4.metric("📊 當日均價", f"{m['avg_price']:.2f}")

        st.divider()

        # 第二排
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("🔔 開盤價", f"{m['open']:.2f}")
        c6.metric("🔺 最高價", f"{m['high']:.2f}")
        c7.metric("🔻 最低價", f"{m['low']:.2f}")
        c8.metric("⚖️ 昨收價", f"{m['prev_close']:.2f}")

    # --- 走勢圖 (價格 + 成交量) ---
    st.markdown("##### 📈 今日走勢 (Trend & Volume)")
    
    # 傳入昨收價 (m['prev_close']) 繪製基準線
    final_chart = draw_combo_chart(df_m, main_color, m['prev_close'])
    
    st.altair_chart(final_chart, use_container_width=True)

# === 頁尾 ===
st.divider()
t_str = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"<div style='text-align: center; color: gray;'>遠東集團_聯稽一處戰情指揮中心 | 開發者：李宗念 | 更新時間：{t_str}</div>", unsafe_allow_html=True)
