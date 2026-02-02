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

# CSS：微軟正黑體 + 數字放大 + 成交量柱狀更明顯（紅色）
st.markdown("""
    <style>
        html, body, [class*="css"] { font-family: 'Microsoft JhengHei', sans-serif !important; }
        div[data-testid="stMetricValue"] { font-size: 2rem !important; font-weight: 700; }
        canvas { border-radius: 0px !important; }
        div[data-testid="stAltairChart"] { margin-top: -20px; }
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

# === 3. 證交所官方大盤數據（全新解析邏輯，徹底容錯）===
@st.cache_data(ttl=8)  # 更頻繁更新
def get_market_stats():
    try:
        url = "https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&type=ALL"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=12)
        data = resp.json()
        if data.get('stat') != 'OK':
            return None
        for row in data.get('data9', []):
            if '發行量加權股價指數' in str(row[0]):
                # 欄位嚴格解析
                current_str = str(row[1]).replace(',', '').strip()
                current = float(current_str) if current_str != '--' else 0.0
                
                change_str = str(row[2]).replace(',', '').strip()
                if change_str.startswith('+'):
                    change = float(change_str[1:])
                elif change_str.startswith('-'):
                    change = -float(change_str[1:])
                else:
                    change = float(change_str) if change_str != '--' else 0.0
                
                pct_str = str(row[3]).replace('%', '').strip()
                if pct_str.startswith('+'):
                    pct = float(pct_str[1:])
                elif pct_str.startswith('-'):
                    pct = -float(pct_str[1:])
                else:
                    pct = float(pct_str) if pct_str != '--' else 0.0
                
                vol_str = str(row[4]).replace(',', '').strip()
                volume = float(vol_str) if vol_str != '--' else 0.0  # 直接為「張」
                
                amount_str = str(row[5]).replace(',', '').strip()
                amount_e = float(amount_str) / 100000000 if amount_str != '--' else 0.0  # 元 → 億
                
                return {
                    'current': current,
                    'change': change,
                    'pct_change': pct,
                    'volume': volume,      # 張
                    'amount_e': amount_e   # 億
                }
        return None
    except:
        return None

# === 4. yfinance 數據（用於高低價、昨收、圖表）===
@st.cache_data(ttl=5)
def get_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info or {}
        fi = stock.fast_info
        fast_info = {
            'last_price': getattr(fi, 'last_price', None),
            'previous_close': getattr(fi, 'previous_close', None),
            'day_high': getattr(fi, 'day_high', None),
            'day_low': getattr(fi, 'day_low', None),
            'last_volume': getattr(fi, 'last_volume', None)
        }
        df_minute = stock.history(period="1d", interval="1m", auto_adjust=False)
        df_daily = stock.history(period="5d", interval="1d", auto_adjust=False)
        if not df_minute.empty:
            df_minute.index = df_minute.index.tz_convert(tw_tz)
            df_minute = df_minute[df_minute.index.time <= time(13, 30)]  # 嚴格避開盤後
        return info, fast_info, df_minute, df_daily
    except:
        return {}, {}, pd.DataFrame(), pd.DataFrame()

def calculate_metrics_safe(info, fast_info, df_minute, df_daily):
    res = {"current": 0.0, "prev_close": 0.0, "change": 0.0, "pct_change": 0.0,
           "high": 0.0, "low": 0.0, "open": 0.0, "volume": 0, "amount_e": 0.0}
    
    prev = info.get('previousClose') or fast_info.get('previous_close')
    if prev is None and not df_daily.empty:
        prev = df_daily['Close'].iloc[-2]
    
    curr = info.get('currentPrice') or fast_info.get('last_price')
    if curr is None and not df_minute.empty:
        curr = df_minute['Close'].iloc[-1]
    if curr is None and not df_daily.empty:
        curr = df_daily['Close'].iloc[-1]
    
    if prev is None or curr is None or prev == 0:
        return res
    
    high = fast_info.get('day_high') or (df_minute['High'].max() if not df_minute.empty else curr)
    low = fast_info.get('day_low') or (df_minute['Low'].min() if not df_minute.empty else curr)
    
    vol = info.get('regularMarketVolume') or fast_info.get('last_volume')
    if (vol is None or vol == 0) and not df_minute.empty:
        vol = df_minute['Volume'].sum()
    
    amount_e = (vol * (high + low + curr) / 3) / 100000000 if vol else 0.0
    
    res.update({
        'current': curr, 'prev_close': prev,
        'change': curr - prev, 'pct_change': (curr - prev) / prev * 100,
        'high': high, 'low': low,
        'open': info.get('regularMarketOpen', curr),
        'volume': vol, 'amount_e': amount_e
    })
    return res

# === 圖表繪製（成交量柱狀改為紅色，更像截圖）===
def draw_chart_combo(df, price_color, prev_close):
    if df.empty: return None
    df = df.reset_index()
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)
    
    y_domain = [df['Close'].min() * 0.999, df['Close'].max() * 1.001]
    
    x_axis = alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M', grid=False))
    
    # 價格區
    area = alt.Chart(df).mark_area(color=price_color, opacity=0.1).encode(x=x_axis, y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain)))
    line = alt.Chart(df).mark_line(color=price_color, strokeWidth=3).encode(x=x_axis, y='Close:Q')
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(strokeDash=[5,5], color='gray').encode(y='y')
    price_chart = (area + line + rule).properties(height=320)
    
    # 成交量區（固定紅色柱狀，更明顯，像截圖）
    vol_chart = alt.Chart(df).mark_bar(color='#ff4444', opacity=0.9, width=12).encode(
        x=alt.X('Time:T', axis=None),
        y=alt.Y('Volume:Q', axis=alt.Axis(title='成交量 (張)', tickCount=4)),
        tooltip=['Time', 'Volume']
    ).properties(height=120)
    
    return alt.vconcat(price_chart, vol_chart, spacing=5).resolve_scale(x='shared')

def draw_mini_chart(df, color, prev_close):
    if df.empty: return None
    df = df.reset_index()
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)
    line = alt.Chart(df).mark_line(color=color, strokeWidth=2.5).encode(
        x=alt.X('Time:T', axis=None),
        y=alt.Y('Close:Q', scale=alt.Scale(zero=False), axis=None)
    )
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(strokeDash=[3,3], color='gray').encode(y='y')
    return (line + rule).properties(height=70)

# === 5. UI ===
st.sidebar.header("🎯 監控標的")
selected_name = st.sidebar.radio("選擇公司：", list(stock_map.keys()))
ticker = stock_map[selected_name]
st.sidebar.markdown("---")
st.sidebar.caption("開發者：李宗念")

with st.container(border=True):
    col_head, col_idx = st.columns([2, 1.5])
    with col_head:
        st.title("🏢 遠東集團戰情中心")
        st.markdown(f"### 🔥 監控：**{selected_name}**")
    
    # 大盤（全新整合：官方金額/量 + yfinance 高低/昨收算振幅）
    _, fast_info, idx_min, _ = get_stock_data("^TWII")
    idx_base = calculate_metrics_safe({}, fast_info, idx_min, pd.DataFrame())
    
    market_stats = get_market_stats()
    if market_stats:
        idx_base.update(market_stats)
    
    if idx_base['current'] > 0:
        idx_color = '#d62728' if idx_base['change'] >= 0 else '#2ca02c'
        amp = (idx_base['high'] - idx_base['low']) / idx_base['prev_close'] * 100 if idx_base['prev_close'] > 0 and idx_base['high'] > 0 else 0.0
        
        with col_idx:
            st.markdown("##### 🇹🇼 加權指數")
            st.metric("", f"{idx_base['current']:,.0f}", 
                      f"{idx_base['change']:+.0f} ({idx_base['pct_change']:+.2f}%)",
                      delta_color="inverse")
            st.markdown(f"**成交金額(億)：** {idx_base['amount_e']:,.2f}")
            st.markdown(f"**成交量(張)　　：** {idx_base['volume']:,.0f}")
            st.markdown(f"**當日振幅　　：** {amp:.2f}%")
            if not idx_min.empty:
                st.altair_chart(draw_mini_chart(idx_min, idx_color, idx_base['prev_close']), use_container_width=True)
    else:
        st.warning("大盤資料載入中...")

# === 6. 個股 ===
info, fast_info, df_m, df_d = get_stock_data(ticker)
m = calculate_metrics_safe(info, fast_info, df_m, df_d)

if m['current'] > 0:
    main_color = '#d62728' if m['change'] >= 0 else '#2ca02c'
    
    with st.container(border=True):
        cols = st.columns(4)
        cols[0].metric("💰 目前股價", f"{m['current']:.2f}", f"{m['change']:+.2f} ({m['pct_change']:+.2f}%)", delta_color="inverse")
        cols[1].metric("💎 成交金額(億)", f"{m['amount_e']:,.2f}")
        cols[2].metric("📦 總成交量(張)", f"{m['volume']/1000:,.0f}")
        cols[3].metric("⚖️ 昨收", f"{m['prev_close']:.2f}")
        
        st.divider()
        
        cols2 = st.columns(4)
        cols2[0].metric("🔔 開盤", f"{m['open']:.2f}")
        cols2[1].metric("🔺 最高", f"{m['high']:.2f}")
        cols2[2].metric("🔻 最低", f"{m['low']:.2f}")
        amp_stock = (m['high'] - m['low']) / m['prev_close'] * 100 if m['prev_close'] > 0 else 0
        cols2[3].metric("〰️ 振幅", f"{amp_stock:.2f}%")
    
    st.markdown("##### 📈 今日走勢（價格＋成交量）")
    if not df_m.empty:
        st.altair_chart(draw_chart_combo(df_m, main_color, m['prev_close']), use_container_width=True)
    else:
        st.info("🕒 盤前/休市無分鐘資料，上方為最新日線資訊")
else:
    st.error("⚠️ 連線失敗，請重新整理")

st.divider()
now = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"<div style='text-align: center; color: gray;'>遠東集團戰情中心 | 開發者：李宗念 | 更新：{now}</div>", unsafe_allow_html=True)
