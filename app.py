import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime, time
import pytz

# === 1. 系統初始化 ===
st.set_page_config(page_title="遠東集團戰情中心", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

# 強制 CSS
st.markdown("""
    <style>
        html, body, [class*="css"] {
            font-family: 'Microsoft JhengHei', '微軟正黑體', sans-serif !important;
        }
        div[data-testid="stMetricValue"] {
            font-size: 2rem !important;
            font-weight: 700;
        }
        canvas {
            border-radius: 0px !important;
        }
        div[data-testid="stAltairChart"] {
            margin-top: -10px;
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

# === 3. 核心數據引擎 (嚴格過濾盤後) ===

@st.cache_data(ttl=5)
def get_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        
        # 1. 抓日線 (5天)：設定 auto_adjust=False 以確保拿到「原始價格」(跟 Yahoo 網頁一致)
        df_daily = stock.history(period="5d", interval="1d", auto_adjust=False)
        
        # 2. 抓分鐘線 (1天)：設定 auto_adjust=False
        df_minute = stock.history(period="1d", interval="1m", auto_adjust=False)
        
        # === 關鍵修正：時區轉換與盤後過濾 ===
        if not df_minute.empty:
            # 轉成台北時間
            df_minute.index = df_minute.index.tz_convert(tw_tz)
            
            # 過濾：只保留 13:30 (含) 以前的數據
            # 這樣可以剔除 14:00 後的盤後定價交易，確保成交量跟 Yahoo 網頁一致
            market_close_time = time(13, 31) # 設定 13:31 是為了包含 13:30 整的那一筆
            df_minute = df_minute[df_minute.index.time < market_close_time]
            
        return df_daily, df_minute
    except:
        return pd.DataFrame(), pd.DataFrame()

def calculate_metrics_strict(df_daily, df_minute):
    """
    計算邏輯：完全依賴「過濾後的盤中數據」
    """
    if df_minute.empty: return None
    
    # === A. 鎖定「昨收價」 ===
    # 從日線抓，因為日線包含完整的歷史
    # 邏輯：找日期「嚴格小於」今天日期的最後一筆
    today_date = df_minute.index[-1].date()
    past_daily = df_daily[df_daily.index.date < today_date]
    
    if not past_daily.empty:
        prev_close = past_daily['Close'].iloc[-1]
    else:
        prev_close = df_minute['Open'].iloc[0] # 防呆

    # === B. 鎖定「目前股價」 ===
    # 拿過濾後分鐘線的最後一筆 (這就是 13:30 收盤價，不含盤後)
    current_price = df_minute['Close'].iloc[-1]
    
    # === C. 鎖定「成交量」 (Yahoo 網頁顯示的量) ===
    # 直接加總過濾後的分鐘線成交量
    # 這樣就排除了盤後定價的量
    total_volume = df_minute['Volume'].sum()
    
    # === D. 估算「成交金額」 (不含盤後) ===
    # 累加 (每分鐘收盤價 * 每分鐘成交量)
    turnover_est = (df_minute['Close'] * df_minute['Volume']).sum()

    # === E. 漲跌 ===
    change = current_price - prev_close
    pct_change = (change / prev_close) * 100

    return {
        "current": current_price,
        "prev_close": prev_close,
        "change": change,
        "pct_change": pct_change,
        "high": df_minute['High'].max(),
        "low": df_minute['Low'].min(),
        "open": df_minute['Open'].iloc[0],
        "volume": total_volume,
        "amount_e": turnover_est / 100000000, # 換算億
    }

def draw_chart_combo(df, color, prev_close):
    """繪製圖表：價格 + 成交量"""
    if df.empty: return None
    
    df = df.reset_index()
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)
    
    # Y 軸動態範圍 (強制放大波動)
    y_min = df['Close'].min()
    y_max = df['Close'].max()
    diff = y_max - y_min
    buffer = 0.05 if diff < 0.1 else diff * 0.1
    y_domain = [y_min - buffer, y_max + buffer]
    
    x_axis = alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M', grid=False))
    
    # 價格圖
    area = alt.Chart(df).mark_area(color=color, opacity=0.1).encode(
        x=x_axis, y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain), axis=alt.Axis(title='股價', grid=True))
    )
    line = alt.Chart(df).mark_line(color=color, strokeWidth=2).encode(
        x=x_axis, y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain)),
        tooltip=['Time', 'Close', 'Volume']
    )
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(
        strokeDash=[4, 4], color='gray', opacity=0.8
    ).encode(y='y')
    
    price_chart = (area + line + rule).properties(height=300)
    
    # 成交量圖
    vol_chart = alt.Chart(df).mark_bar(color=color, opacity=0.5).encode(
        x=alt.X('Time:T', axis=None),
        y=alt.Y('Volume:Q', axis=alt.Axis(title='量', tickCount=3)),
        tooltip=['Time', 'Volume']
    ).properties(height=80)
    
    return alt.vconcat(price_chart, vol_chart, spacing=0).resolve_scale(x='shared')

def draw_mini_chart(df, color, prev_close):
    """大盤迷你圖"""
    if df.empty: return None
    df = df.reset_index()
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)
    
    y_min = df['Close'].min()
    y_max = df['Close'].max()
    y_domain = [y_min, y_max]

    line = alt.Chart(df).mark_line(color=color, strokeWidth=2).encode(
        x=alt.X('Time:T', axis=None),
        y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain, zero=False), axis=None),
        tooltip=['Time', 'Close']
    )
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(
        strokeDash=[2, 2], color='gray', opacity=0.5
    ).encode(y='y')
    
    return (line + rule).properties(height=60)

# === 4. 側邊欄 ===
st.sidebar.header("🎯 監控標的選擇")
selected_name = st.sidebar.radio("請選擇公司：", list(stock_map.keys()))
ticker = stock_map[selected_name]
st.sidebar.markdown("---")
st.sidebar.caption(f"✅ 系統連線正常 | 開發者：李宗念")

# === 5. 戰情儀表板 ===
with st.container(border=True):
    col_head, col_idx_text, col_idx_chart = st.columns([2, 0.8, 1.2])
    
    with col_head:
        st.title("🏢 遠東集團戰情中心")
        st.markdown(f"### 🔥 目前監控：**{selected_name}**")
        
    # 大盤 (也要套用嚴格計算)
    idx_daily, idx_min = get_stock_data("^TWII")
    if not idx_min.empty:
        idx_m = calculate_metrics_strict(idx_daily, idx_min)
        if idx_m:
            idx_color = '#d62728' if idx_m['change'] >= 0 else '#2ca02c'
            with col_idx_text:
                st.markdown("##### 🇹🇼 加權指數")
                st.metric("Index", f"{idx_m['current']:,.0f}", f"{idx_m['change']:+.0f} ({idx_m['pct_change']:+.2f}%)", delta_color="inverse", label_visibility="collapsed")
            with col_idx_chart:
                st.altair_chart(draw_mini_chart(idx_min, idx_color, idx_m['prev_close']), use_container_width=True)

# === 6. 個股數據 ===
df_d, df_m = get_stock_data(ticker)

if df_m.empty:
    st.error("⚠️ 暫無數據 (請確認開盤時間)")
else:
    m = calculate_metrics_strict(df_d, df_m)
    main_color = '#d62728' if m['change'] >= 0 else '#2ca02c'
    
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 目前股價", f"{m['current']:.2f}", f"{m['change']:+.2f} ({m['pct_change']:+.2f}%)", delta_color="inverse")
        c2.metric("💎 成交金額 (估)", f"{m['amount_e']:.2f} 億")
        c3.metric("📦 總成交量", f"{m['volume']/1000:,.0f} 張")
        c4.metric("⚖️ 昨收價", f"{m['prev_close']:.2f}")
        
        st.divider()
        
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("🔔 開盤價", f"{m['open']:.2f}")
        c6.metric("🔺 最高價", f"{m['high']:.2f}")
        c7.metric("🔻 最低價", f"{m['low']:.2f}")
        # 當日振幅
        amp = ((m['high'] - m['low']) / m['prev_close']) * 100
        c8.metric("〰️ 當日振幅", f"{amp:.2f}%")

    # === 7. 圖表 ===
    st.markdown("##### 📈 今日走勢 (Trend & Volume)")
    st.altair_chart(draw_chart_combo(df_m, main_color, m['prev_close']), use_container_width=True)

# === 頁尾 ===
st.divider()
t_str = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"<div style='text-align: center; color: gray;'>遠東集團_聯稽一處戰情指揮中心 | 開發者：李宗念 | 更新時間：{t_str}</div>", unsafe_allow_html=True)
