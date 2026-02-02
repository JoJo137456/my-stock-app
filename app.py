import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime, time
import pytz
import requests

# === 1. 系統初始化 ===
st.set_page_config(page_title="遠東集團戰情中心", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

# CSS 樣式
st.markdown("""
    <style>
        html, body, [class*="css"] {
            font-family: 'Microsoft JhengHei', '微軟正黑體', sans-serif !important;
        }
        div[data-testid="stMetricValue"] {
            font-size: 2rem !important;
            font-weight: 700;
        }
        canvas { border-radius: 0px !important; }
        div[data-testid="stAltairChart"] { margin-top: -10px; }
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

# === 3. 證交所官方大盤數據（加強版）===
@st.cache_data(ttl=10)
def get_market_stats():
    try:
        url = "https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&type=ALL"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if data.get('stat') != 'OK':
            return None
            
        for row in data.get('data9', []):
            if '發行量加權股價指數' in str(row[0]).strip():
                # 價格
                current = float(str(row[1]).replace(',', ''))
                # 漲跌
                change_str = str(row[2]).replace(',', '')
                change = float(change_str) if change_str not in ['--', ''] else 0.0
                # 漲跌幅
                pct_str = str(row[3]).replace('%', '').strip()
                pct = float(pct_str) if pct_str not in ['--', ''] else 0.0
                # 成交量（張，已是正確單位，無需再除）
                vol_str = str(row[4]).replace(',', '')
                vol = float(vol_str) if vol_str not in ['--', ''] else 0.0
                # 成交金額（億元）
                amount_str = str(row[5]).replace(',', '')
                amount_e = float(amount_str) / 100000000 if amount_str not in ['--', ''] else 0.0
                
                return {
                    'current': current,
                    'change': change,
                    'pct_change': pct,
                    'volume': vol,
                    'amount_e': amount_e
                }
        return None
    except Exception:
        return None

# === 4. yfinance 數據引擎（維持不變）===
@st.cache_data(ttl=5)
def get_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info if stock.info else {}
        fi = stock.fast_info
        fast_info_dict = {
            'last_price': getattr(fi, 'last_price', None),
            'previous_close': getattr(fi, 'previous_close', None),
            'last_volume': getattr(fi, 'last_volume', None),
            'day_high': getattr(fi, 'day_high', None),
            'day_low': getattr(fi, 'day_low', None)
        }
        df_minute = stock.history(period="1d", interval="1m", auto_adjust=False)
        df_daily = stock.history(period="5d", interval="1d", auto_adjust=False)
        if not df_minute.empty:
            df_minute.index = df_minute.index.tz_convert(tw_tz)
            df_minute = df_minute[df_minute.index.time < time(13, 35)]
        return info, fast_info_dict, df_minute, df_daily
    except Exception:
        return {}, {}, pd.DataFrame(), pd.DataFrame()

# === 其餘函數（calculate_metrics_safe、draw_chart_combo、draw_mini_chart）維持原樣 ===
# （為節省篇幅，此處省略，沿用上版程式碼的相同函數）

def calculate_metrics_safe(info, fast_info, df_minute, df_daily):
    res = {
        "current": 0.0, "prev_close": 0.0, "change": 0.0, "pct_change": 0.0,
        "high": 0.0, "low": 0.0, "open": 0.0, "volume": 0, "amount_e": 0.0
    }
    prev = info.get('previousClose') or fast_info.get('previous_close')
    if prev is None and not df_daily.empty: prev = df_daily['Close'].iloc[-2]
    curr = info.get('currentPrice') or fast_info.get('last_price')
    if curr is None and not df_minute.empty: curr = df_minute['Close'].iloc[-1]
    if curr is None and not df_daily.empty: curr = df_daily['Close'].iloc[-1]
    if prev is None or curr is None: return res

    vol = info.get('regularMarketVolume') or info.get('volume') or fast_info.get('last_volume')
    if (vol is None or vol == 0) and not df_minute.empty: vol = df_minute['Volume'].sum()

    h = fast_info.get('day_high') or (df_minute['High'].max() if not df_minute.empty else None)
    l = fast_info.get('day_low') or (df_minute['Low'].min() if not df_minute.empty else None)
    if h is None: h = curr
    if l is None: l = curr

    avg_p = (h + l + curr) / 3
    amount = vol * avg_p if vol else 0

    res.update({
        'current': curr, 'prev_close': prev,
        'change': curr - prev, 'pct_change': (curr - prev) / prev * 100,
        'high': h, 'low': l, 'open': info.get('open', curr),
        'volume': vol, 'amount_e': amount / 100000000
    })
    return res

def draw_chart_combo(df, color, prev_close):
    if df.empty: return None
    df = df.reset_index()
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)

    y_min, y_max = df['Close'].min(), df['Close'].max()
    diff = y_max - y_min
    buffer = 0.05 if diff < 0.1 else diff * 0.1
    y_domain = [y_min - buffer, y_max + buffer]

    x_axis = alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M', grid=False))

    area = alt.Chart(df).mark_area(color=color, opacity=0.1).encode(x=x_axis, y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain), axis=alt.Axis(title='股價')))
    line = alt.Chart(df).mark_line(color=color, strokeWidth=2).encode(x=x_axis, y='Close:Q', tooltip=['Time', 'Close', 'Volume'])
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(strokeDash=[4, 4], color='gray').encode(y='y')
    price_chart = (area + line + rule).properties(height=300)

    vol_chart = alt.Chart(df).mark_bar(color=color, opacity=0.9, width=10).encode(
        x=alt.X('Time:T', axis=None),
        y=alt.Y('Volume:Q', axis=alt.Axis(title='成交量', tickCount=3)),
        tooltip=['Time', 'Volume']
    ).properties(height=100)

    return alt.vconcat(price_chart, vol_chart, spacing=0).resolve_scale(x='shared')

def draw_mini_chart(df, color, prev_close):
    if df.empty: return None
    df = df.reset_index()
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)
    line = alt.Chart(df).mark_line(color=color, strokeWidth=2).encode(
        x=alt.X('Time:T', axis=None),
        y=alt.Y('Close:Q', scale=alt.Scale(domain=[df['Close'].min(), df['Close'].max()], zero=False), axis=None)
    )
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(strokeDash=[2, 2], color='gray', opacity=0.5).encode(y='y')
    return (line + rule).properties(height=60)

# === 5. 側邊欄與主畫面（大盤部分加強提示）===
st.sidebar.header("🎯 監控標的選擇")
selected_name = st.sidebar.radio("請選擇公司：", list(stock_map.keys()))
ticker = stock_map[selected_name]
st.sidebar.markdown("---")
st.sidebar.caption("✅ 系統連線正常 | 開發者：李宗念")

with st.container(border=True):
    col_head, col_idx_text, col_idx_chart = st.columns([2, 0.8, 1.2])
    with col_head:
        st.title("🏢 遠東集團戰情中心")
        st.markdown(f"### 🔥 目前監控：**{selected_name}**")

    # 大盤數據
    info, fast_info, idx_min, idx_d = get_stock_data("^TWII")
    idx_m = calculate_metrics_safe(info, fast_info, idx_min, idx_d)
    market_stats = get_market_stats()

    if market_stats:
        idx_m.update(market_stats)
        amount_text = f"{idx_m['amount_e']:.2f} 億"
        volume_text = f"{idx_m['volume']:,.0f} 張"
    else:
        amount_text = "讀取中（可能休市或連線問題）"
        volume_text = f"{idx_m['volume']:,.0f} 張（估）"

    if idx_m['current'] != 0:
        idx_color = '#d62728' if idx_m['change'] >= 0 else '#2ca02c'
        with col_idx_text:
            st.markdown("##### 🇹🇼 加權指數")
            st.metric("Index", f"{idx_m['current']:,.0f}",
                      f"{idx_m['change']:+.0f} ({idx_m['pct_change']:+.2f}%)",
                      delta_color="inverse", label_visibility="collapsed")
            st.markdown(f"**成交金額：** {amount_text}")
            st.markdown(f"**成交量　：** {volume_text}")
        with col_idx_chart:
            if not idx_min.empty:
                st.altair_chart(draw_mini_chart(idx_min, idx_color, idx_m['prev_close']), use_container_width=True)
    else:
        st.warning("大盤數據讀取中...")

# === 6. 個股部分（維持不變，圖表已含即時價格＋成交量）===
info, fast_info, df_m, df_d = get_stock_data(ticker)
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

    st.markdown("##### 📈 今日走勢 (Trend & Volume)")
    if not df_m.empty:
        st.altair_chart(draw_chart_combo(df_m, main_color, m['prev_close']), use_container_width=True)
    else:
        st.info("🕒 目前無即時分鐘走勢（可能是盤前或休市），但上方數據已顯示最新資訊。")
else:
    st.error("⚠️ 數據連線失敗，請檢查網路或稍後再試。")

# === 頁尾 ===
st.divider()
t_str = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"<div style='text-align: center; color: gray;'>遠東集團_聯稽一處戰情指揮中心 | 開發者：李宗念 | 更新時間：{t_str}</div>", unsafe_allow_html=True)
