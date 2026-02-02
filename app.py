import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime, time
import pytz

# === 1. 系統初始化 ===
st.set_page_config(page_title="遠東集團戰情中心", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

# 強制 CSS：微軟正黑體 + 數字放大 + 去除圖表留白
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

# === 3. 核心數據引擎 (解決快取報錯 + 官方數據優先) ===

@st.cache_data(ttl=5)
def get_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        
        # 1. 取得官方資訊 (info) - 轉成字典避免報錯
        info = stock.info if stock.info else {}
        
        # 2. 取得 Fast Info (關鍵修正：轉成字典！)
        # 直接回傳 fast_info 物件會導致 Streamlit 報錯，所以我們要手動拆解
        fi = stock.fast_info
        fast_info_dict = {
            'last_price': fi.last_price,
            'previous_close': fi.previous_close,
            'last_volume': fi.last_volume,
            'day_high': fi.day_high,
            'day_low': fi.day_low
        }
        
        # 3. 抓分鐘線 (純粹為了畫圖)
        df_minute = stock.history(period="1d", interval="1m", auto_adjust=False)
        
        # 過濾分鐘線：只留 13:35 以前的 (避免盤後定價拉出一條直線)
        if not df_minute.empty:
            df_minute.index = df_minute.index.tz_convert(tw_tz)
            market_close_time = time(13, 35) 
            df_minute = df_minute[df_minute.index.time < market_close_time]

        return info, fast_info_dict, df_minute
    except Exception as e:
        return {}, {}, pd.DataFrame()

def calculate_metrics_official(info, fast_info, df_minute):
    """
    計算邏輯：接收簡單字典，不再接收複雜物件
    """
    if df_minute.empty: return None

    # === A. 昨收價 (Previous Close) ===
    # 優先從 info 拿 (Yahoo 網頁顯示值)
    prev_close = info.get('previousClose')
    # 如果 info 沒給，從 fast_info 字典拿
    if prev_close is None: prev_close = fast_info.get('previous_close')

    # === B. 目前股價 (Current Price) ===
    current_price = info.get('currentPrice')
    if current_price is None: current_price = fast_info.get('last_price')
    # 防呆
    if current_price is None: current_price = df_minute['Close'].iloc[-1]

    # === C. 總成交量 (Volume) ===
    # 這是「股數」，顯示時要除以 1000
    total_volume_shares = info.get('volume')
    if total_volume_shares is None: total_volume_shares = fast_info.get('last_volume')
    
    # 如果 info 的 volume 是 0 (盤中可能)，回退用分鐘線加總
    if total_volume_shares is None or total_volume_shares == 0:
        total_volume_shares = df_minute['Volume'].sum()

    # === D. 漲跌 ===
    change = current_price - prev_close
    pct_change = (change / prev_close) * 100

    # === E. 成交金額 (估算) ===
    day_high = fast_info.get('day_high', df_minute['High'].max())
    day_low = fast_info.get('day_low', df_minute['Low'].min())
    
    # 處理 NaN
    if pd.isna(day_high): day_high = df_minute['High'].max()
    if pd.isna(day_low): day_low = df_minute['Low'].min()

    avg_p = (day_high + day_low + current_price) / 3
    turnover_est = total_volume_shares * avg_p

    return {
        "current": current_price,
        "prev_close": prev_close,
        "change": change,
        "pct_change": pct_change,
        "high": day_high,
        "low": day_low,
        "open": info.get('open', df_minute['Open'].iloc[0]),
        "volume_shares": total_volume_shares, # 這是股數
        "amount_e": turnover_est / 100000000, # 億
    }

def draw_chart_combo(df, color, prev_close):
    """繪製圖表：價格(上) + 成交量(下)"""
    if df.empty: return None
    
    df = df.reset_index()
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)
    
    # 強制放大波動
    y_min = df['Close'].min()
    y_max = df['Close'].max()
    diff = y_max - y_min
    buffer = 0.05 if diff < 0.1 else diff * 0.1
    y_domain = [y_min - buffer, y_max + buffer]
    
    # X軸設定 (共用)
    x_axis = alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M', grid=False))
    
    # === 上圖：價格走勢 ===
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
    
    # === 下圖：成交量柱狀圖 ===
    # 使用獨立的 Y 軸，避免跟股價混在一起
    vol_chart = alt.Chart(df).mark_bar(color=color, opacity=0.5).encode(
        x=alt.X('Time:T', axis=None), # 隱藏 X 軸文字，對齊上方
        y=alt.Y('Volume:Q', axis=alt.Axis(title='成交量', tickCount=3)),
        tooltip=['Time', 'Volume']
    ).properties(height=80) # 高度設為 80px
    
    # 垂直組合 (VConcat)
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
        
    # 大盤
    info, fast_info, idx_min = get_stock_data("^TWII")
    if not idx_min.empty:
        idx_m = calculate_metrics_official(info, fast_info, idx_min)
        if idx_m:
            idx_color = '#d62728' if idx_m['change'] >= 0 else '#2ca02c'
            with col_idx_text:
                st.markdown("##### 🇹🇼 加權指數")
                st.metric("Index", f"{idx_m['current']:,.0f}", f"{idx_m['change']:+.0f} ({idx_m['pct_change']:+.2f}%)", delta_color="inverse", label_visibility="collapsed")
            with col_idx_chart:
                st.altair_chart(draw_mini_chart(idx_min, idx_color, idx_m['prev_close']), use_container_width=True)

# === 6. 個股數據 ===
info, fast_info, df_m = get_stock_data(ticker)

if df_m.empty:
    st.error("⚠️ 暫無數據")
else:
    m = calculate_metrics_official(info, fast_info, df_m)
    main_color = '#d62728' if m['change'] >= 0 else '#2ca02c'
    
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 目前股價", f"{m['current']:.2f}", f"{m['change']:+.2f} ({m['pct_change']:+.2f}%)", delta_color="inverse")
        c2.metric("💎 成交金額 (估)", f"{m['amount_e']:.2f} 億")
        # 修正重點：這裡除以 1000，把「股」變成「張」
        c3.metric("📦 總成交量", f"{m['volume_shares']/1000:,.0f} 張")
        c4.metric("⚖️ 昨收價", f"{m['prev_close']:.2f}")
        
        st.divider()
        
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("🔔 開盤價", f"{m['open']:.2f}")
        c6.metric("🔺 最高價", f"{m['high']:.2f}")
        c7.metric("🔻 最低價", f"{m['low']:.2f}")
        amp = ((m['high'] - m['low']) / m['prev_close']) * 100
        c8.metric("〰️ 當日振幅", f"{amp:.2f}%")

    # === 7. 圖表 ===
    st.markdown("##### 📈 今日走勢 (Trend & Volume)")
    # 這裡會畫出 價格(上) + 成交量(下)
    st.altair_chart(draw_chart_combo(df_m, main_color, m['prev_close']), use_container_width=True)

# === 頁尾 ===
st.divider()
t_str = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"<div style='text-align: center; color: gray;'>遠東集團_聯稽一處戰情指揮中心 | 開發者：李宗念 | 更新時間：{t_str}</div>", unsafe_allow_html=True)
