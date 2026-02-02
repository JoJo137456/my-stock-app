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

# === 3. 核心數據引擎 (最穩固版) ===

@st.cache_data(ttl=5)
def get_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        
        # 1. 抓取官方 Info (轉字典，防止快取報錯)
        info = stock.info if stock.info else {}
        
        # 2. 抓取 Fast Info (轉字典，防止快取報錯)
        fi = stock.fast_info
        fast_info_dict = {}
        try:
            # 針對大盤指數，某些屬性可能不存在，用 get 保護
            fast_info_dict = {
                'last_price': getattr(fi, 'last_price', None),
                'previous_close': getattr(fi, 'previous_close', None),
                'last_volume': getattr(fi, 'last_volume', None),
                'day_high': getattr(fi, 'day_high', None),
                'day_low': getattr(fi, 'day_low', None)
            }
        except:
            pass

        # 3. 抓分鐘線 (畫圖用)
        df_minute = stock.history(period="1d", interval="1m", auto_adjust=False)
        
        # 4. 抓日線 (備用，萬一分鐘線掛掉，至少有東西看)
        df_daily = stock.history(period="5d", interval="1d", auto_adjust=False)

        # 時間過濾：只留 13:35 以前 (避免盤後定價拉直線)
        if not df_minute.empty:
            df_minute.index = df_minute.index.tz_convert(tw_tz)
            market_close_time = time(13, 35) 
            df_minute = df_minute[df_minute.index.time < market_close_time]

        return info, fast_info_dict, df_minute, df_daily
    except Exception as e:
        # 發生錯誤時回傳空值，但不讓程式崩潰
        return {}, {}, pd.DataFrame(), pd.DataFrame()

def calculate_metrics_safe(info, fast_info, df_minute, df_daily):
    """
    計算邏輯：安全模式，確保永遠有數字回傳
    """
    # 預設值
    res = {
        "current": 0.0, "prev_close": 0.0, "change": 0.0, "pct_change": 0.0,
        "high": 0.0, "low": 0.0, "open": 0.0, "volume": 0, "amount_e": 0.0
    }
    
    # === 1. 價格來源 (優先順序: Info > FastInfo > Minute > Daily) ===
    # 昨收
    prev = info.get('previousClose')
    if prev is None: prev = fast_info.get('previous_close')
    if prev is None and not df_daily.empty: prev = df_daily['Close'].iloc[-2] # 拿昨日
    
    # 現價
    curr = info.get('currentPrice')
    if curr is None: curr = fast_info.get('last_price')
    if curr is None and not df_minute.empty: curr = df_minute['Close'].iloc[-1]
    if curr is None and not df_daily.empty: curr = df_daily['Close'].iloc[-1]
    
    # 防呆
    if prev is None or curr is None: return res

    # === 2. 成交量 (Volume) ===
    # 優先抓 regularMarketVolume (常規交易量，不含盤後)
    vol = info.get('regularMarketVolume')
    if vol is None: vol = info.get('volume')
    if vol is None: vol = fast_info.get('last_volume')
    if (vol is None or vol == 0) and not df_minute.empty: vol = df_minute['Volume'].sum()
    
    # === 3. 成交金額 (估算) ===
    # Yahoo 不直接提供成交金額，我們用 (均價 * 總量) 估算
    # 取得當日高低
    h = fast_info.get('day_high')
    if h is None and not df_minute.empty: h = df_minute['High'].max()
    l = fast_info.get('day_low')
    if l is None and not df_minute.empty: l = df_minute['Low'].min()
    
    # 如果還是拿不到高低 (例如剛開盤)，就用現價
    if h is None: h = curr
    if l is None: l = curr
    
    avg_p = (h + l + curr) / 3
    amount = vol * avg_p if vol else 0

    # === 4. 填入結果 ===
    res['current'] = curr
    res['prev_close'] = prev
    res['change'] = curr - prev
    res['pct_change'] = (res['change'] / prev) * 100
    res['high'] = h
    res['low'] = l
    res['open'] = info.get('open', curr) # 沒開盤價就用現價頂著
    res['volume'] = vol
    res['amount_e'] = amount / 100000000 # 億

    return res

def draw_chart_combo(df, color, prev_close):
    """繪製圖表：價格(上) + 成交量(下)"""
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
    
    # === 下圖：成交量柱狀圖 (不透明) ===
    vol_chart = alt.Chart(df).mark_bar(color=color, opacity=1.0).encode(
        x=alt.X('Time:T', axis=None), 
        y=alt.Y('Volume:Q', axis=alt.Axis(title='成交量', tickCount=3)),
        tooltip=['Time', 'Volume']
    ).properties(height=100)
    
    # 垂直組合
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
    info, fast_info, idx_min, idx_d = get_stock_data("^TWII")
    
    # 計算數據 (即使沒抓到分鐘線，也會嘗試用日線計算，防止空白)
    idx_m = calculate_metrics_safe(info, fast_info, idx_min, idx_d)
    
    if idx_m['current'] != 0:
        idx_color = '#d62728' if idx_m['change'] >= 0 else '#2ca02c'
        with col_idx_text:
            st.markdown("##### 🇹🇼 加權指數")
            st.metric("Index", f"{idx_m['current']:,.0f}", f"{idx_m['change']:+.0f} ({idx_m['pct_change']:+.2f}%)", delta_color="inverse", label_visibility="collapsed")
            # 顯示大盤成交金額
            st.markdown(f"**成交金額：** {idx_m['amount_e']:.2f} 億")

        with col_idx_chart:
            if not idx_min.empty:
                st.altair_chart(draw_mini_chart(idx_min, idx_color, idx_m['prev_close']), use_container_width=True)
    else:
        st.warning("大盤數據讀取中...")

# === 6. 個股數據 ===
info, fast_info, df_m, df_d = get_stock_data(ticker)

# 計算數據 (安全模式)
m = calculate_metrics_safe(info, fast_info, df_m, df_d)

if m['current'] != 0:
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
        amp = ((m['high'] - m['low']) / m['prev_close']) * 100 if m['prev_close'] != 0 else 0
        c8.metric("〰️ 當日振幅", f"{amp:.2f}%")

    # === 7. 圖表 ===
    st.markdown("##### 📈 今日走勢 (Trend & Volume)")
    if not df_m.empty:
        st.altair_chart(draw_chart_combo(df_m, main_color, m['prev_close']), use_container_width=True)
    else:
        st.info("🕒 目前無即時分鐘走勢 (可能是盤前或休市)，但上方數據已顯示最新日線資訊。")
else:
    st.error("⚠️ 數據連線失敗，請檢查網路或稍後再試。")

# === 頁尾 ===
st.divider()
t_str = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"<div style='text-align: center; color: gray;'>遠東集團_聯稽一處戰情指揮中心 | 開發者：李宗念 | 更新時間：{t_str}</div>", unsafe_allow_html=True)
