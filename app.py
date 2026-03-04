import streamlit as st
import twstock
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, time as dt_time
import pytz
import requests
import urllib3
import yfinance as yf
import base64
import os

# === 0. System Level Fixes ===
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
original_request = requests.Session.request
def patched_request(self, method, url, *args, **kwargs):
    kwargs['verify'] = False
    return original_request(self, method, url, *args, **kwargs)
requests.Session.request = patched_request

# === 1. Dashboard Initialization ===
st.set_page_config(page_title="FENC Audit HQ | Strategic Dashboard", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

# === 最終版工業 SCADA 登入介面 ===
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True

    # 背景圖
    if os.path.exists('bg.jpg'):
        with open('bg.jpg', 'rb') as f:
            encoded_bg = base64.b64encode(f.read()).decode()
        bg_css = f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded_bg}") !important;
            background-size: cover !important;
            background-position: center !important;
            background-attachment: fixed !important;
        }}
        .stApp::before {{
            content: '';
            position: fixed;
            inset: 0;
            background: linear-gradient(rgba(0,0,0,0.75), rgba(0,0,0,0.85));
            z-index: -1;
        }}
        </style>
        """
        st.markdown(bg_css, unsafe_allow_html=True)

    # 調整後的 SCADA 工業風 CSS
    st.markdown("""
    <style>
        [data-testid="stSidebar"], header, [data-testid="collapsedControl"] {display: none !important;}
        
        /* 主卡片 */
        .scada-card {
            background: rgba(15, 18, 25, 0.92);
            backdrop-filter: blur(24px);
            border: 2px solid #00ff9f;
            border-radius: 18px;
            padding: 60px 55px 50px;
            max-width: 460px;
            margin: 90px auto 40px;
            box-shadow: 0 0 40px rgba(0, 255, 159, 0.25), 0 25px 60px rgba(0, 0, 0, 0.8);
        }
        
        /* 標題 - 強 neon 發光 */
        .scada-title {
            font-size: 42px;
            font-weight: 900;
            color: #ffffff;
            text-align: center;
            letter-spacing: 3px;
            margin-bottom: 8px;
            text-shadow: 0 0 15px #00ff9f, 0 0 30px #00ff9f, 0 0 45px #00ff9f;
        }
        
        /* 副標題 - neon 發光 */
        .scada-subtitle {
            font-size: 17px;
            color: #a0f0d0;
            text-align: center;
            margin-bottom: 50px;
            font-weight: 500;
            text-shadow: 0 0 12px #00ff9f;
        }
        
        /* 標籤 - 強烈 neon 發光 (與標題相同風格) */
        .scada-label {
            font-size: 14px;
            font-weight: 700;
            color: #00ff9f;
            margin: 25px 0 8px 0;
            letter-spacing: 2px;
            text-transform: uppercase;
            display: block;
            text-align: center;
            text-shadow: 0 0 10px #00ff9f, 0 0 20px #00ff9f, 0 0 30px #00ff9f;
        }
        
        /* ORGANIZATION 的純白文字 */
        .scada-org-text {
            color: #ffffff;
            font-size: 18px;
            font-weight: 600;
            text-align: center;
            letter-spacing: 1px;
            margin-bottom: 25px;
            text-shadow: 0 0 5px rgba(255, 255, 255, 0.5);
        }
        
        /* 輸入框 - 完全移除外框，改為透明與完美置中 */
        div[data-baseweb="input"] > div {
            background-color: transparent !important;
            border: none !important;
            border-bottom: 1px solid rgba(0, 255, 159, 0.3) !important;
            border-radius: 0 !important;
            height: 45px !important;
            box-shadow: none !important;
        }
        div[data-baseweb="input"] input {
            color: #ffffff !important;
            text-align: center !important;
            font-size: 20px !important;
            font-weight: 500 !important;
            padding: 0 !important; /* 確保完美置中 */
            letter-spacing: 1.5px;
        }
        /* 隱藏輸入框右側的清除 (X) 圖示，避免文字被擠歪 */
        div[data-baseweb="input"] > div > div:nth-child(2) {
            display: none !important;
        }
        /* 輸入時的底部發光特效 */
        div[data-baseweb="input"]:focus-within > div {
            border-color: transparent !important;
            border-bottom: 2px solid #00ff9f !important;
            box-shadow: 0 15px 15px -15px rgba(0, 255, 159, 0.8) !important;
        }
        
        /* Sign In 按鈕 */
        button[kind="primary"] {
            background: linear-gradient(90deg, #00b8ff, #0090ff) !important;
            color: #ffffff !important;
            font-size: 18px !important;
            font-weight: 700 !important;
            height: 60px !important;
            border-radius: 12px !important;
            margin-top: 35px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
        }
        button[kind="primary"]:hover {
            background: linear-gradient(90deg, #00ff9f, #00b8ff) !important;
            box-shadow: 0 0 30px rgba(0, 255, 159, 0.6);
            transform: scale(1.03);
        }
        
        /* 底部連結 - 強烈 neon 發光 */
        .scada-footer {
            text-align: center;
            margin-top: 45px;
            font-size: 15px;
        }
        .scada-footer a, .scada-footer span {
            color: #00ff9f;
            text-decoration: none;
            font-weight: 700;
            text-shadow: 0 0 10px #00ff9f, 0 0 20px #00ff9f;
            letter-spacing: 0.5px;
        }
        .scada-footer a:hover { text-decoration: underline; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.65, 1])
    with col2:
        with st.container():
            st.markdown('<div class="scada-card">', unsafe_allow_html=True)
            
            st.markdown('<div class="scada-title">AUDIT HQ</div>', unsafe_allow_html=True)
            st.markdown('<div class="scada-subtitle">FENC Corporate Control Access</div>', unsafe_allow_html=True)
            
            # 修改點 1 & 2: 螢光標籤與純白文字 (取代下拉選單)
            st.markdown('<span class="scada-label">ORGANIZATION</span>', unsafe_allow_html=True)
            st.markdown('<div class="scada-org-text">Far Eastern New Century (FENC)</div>', unsafe_allow_html=True)
            
            # 修改點 3 & 4: 螢光標籤與無框完美置中的輸入框
            st.markdown('<span class="scada-label">ACCOUNT ID</span>', unsafe_allow_html=True)
            st.text_input("", value="Audit_HQ_Admin", label_visibility="collapsed", key="acc_id")
            
            st.markdown('<span class="scada-label">PASSWORD</span>', unsafe_allow_html=True)
            pwd = st.text_input("", type="password", label_visibility="collapsed", key="pwd")
            
            if st.button("SIGN IN", type="primary", use_container_width=True):
                if pwd == "AUDIT@01":
                    st.session_state["password_correct"] = True
                    st.rerun()
                elif pwd != "":
                    st.error("❌ ACCESS DENIED — Invalid credentials")
            
            # 修改點 5: 底部發光文字
            st.markdown("""
            <div class="scada-footer">
                <a href="#">Forgot Password</a> <span style="color:#a0f0d0; text-shadow:none;">•</span> <a href="#">IT Support (ext. 6855)</a>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

    return False

if not check_password():
    st.stop()

# === 以下為主儀表板程式碼 (維持原樣) ===
st.markdown("""
    <style>
        .stApp { background: #000000 !important; color: #f5f5f7 !important; }
        .main-title { font-size: 2.6rem; font-weight: 700; color: #f5f5f7; text-align: center; margin: 1.5rem 0; letter-spacing: 1px;}
        .sub-title { font-size: 1.15rem; color: #86868b; text-align: center; margin-bottom: 2.5rem; font-weight: 400;}
        .chart-container {
            background: #1c1c1e; padding: 24px; border-radius: 20px;
            margin-bottom: 24px; border: 1px solid #38383a;
        }
        div[data-testid="metric-container"] {
            background-color: #1c1c1e; border: 1px solid #38383a; padding: 15px;
            border-radius: 16px; text-align: center;
        }
        div[data-testid="metric-container"] > div { color: #f5f5f7 !important; }
        div[data-testid="metric-container"] label { color: #86868b !important; font-weight: 500 !important; font-size: 0.85rem !important; text-transform: uppercase;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">Strategic Control Center</div><div class="sub-title">FENC Audit Headquarters</div>', unsafe_allow_html=True)

def check_market_status(market_type='TW'):
    now = datetime.now(tw_tz)
    if market_type == 'CRYPTO': return "open", "🟢 Open (24H)"
    if market_type == 'US':
        hour = now.hour
        if 21 <= hour or hour < 5: return "open", "🟢 Market Open"
        else: return "closed", "🔴 Market Closed"
    current_time = now.time()
    market_open = dt_time(9, 0)
    market_close = dt_time(13, 35)
    is_weekend = now.weekday() >= 5
    if is_weekend: return "closed", "🔴 Weekend Closed"
    elif market_open <= current_time <= market_close: return "open", "🟢 Trading Active"
    else: return "closed", "🔴 Market Closed"

@st.cache_data(ttl=3600)
def fetch_twse_history_proxy(stock_code):
    try:
        data_list = []
        now = datetime.now()
        dates_to_fetch = []
        curr_month = now.replace(day=1)
        for i in range(6):
            target_date = curr_month - pd.DateOffset(months=i)
            dates_to_fetch.append(target_date.strftime('%Y%m01'))
        for date_str in dates_to_fetch:
            url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={stock_code}"
            r = requests.get(url)
            json_data = r.json()
            if json_data['stat'] == 'OK':
                for row in json_data['data']:
                    date_parts = row[0].split('/')
                    ad_year = int(date_parts[0]) + 1911
                    date_iso = f"{ad_year}-{date_parts[1]}-{date_parts[2]}"
                    def to_float(s):
                        try: return float(s.replace(',', ''))
                        except: return 0.0
                    vol_shares = to_float(row[1])
                    data_list.append({
                        'date': date_iso, 'volume': vol_shares,
                        'open': to_float(row[3]), 'high': to_float(row[4]),
                        'low': to_float(row[5]), 'close': to_float(row[6]),
                    })
        data_list.sort(key=lambda x: x['date'])
        return data_list
    except Exception as e: return None

@st.cache_data(ttl=3600)
def fetch_us_history(ticker_symbol):
    try:
        tk = yf.Ticker(ticker_symbol)
        hist = tk.history(period="6mo")
        data_list = []
        for index, row in hist.iterrows():
            data_list.append({
                'date': index.strftime('%Y-%m-%d'), 'volume': float(row['Volume']),
                'open': float(row['Open']), 'high': float(row['High']),
                'low': float(row['Low']), 'close': float(row['Close'])
            })
        return data_list
    except: return None

@st.cache_data(ttl=300)
def get_intraday_chart_data(stock_code, is_us_source=False):
    try:
        ticker_symbol = stock_code if is_us_source else f"{stock_code}.TW"
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="1d", interval="1m")
        if df.empty:
            df = ticker.history(period="5d", interval="5m")
            if not df.empty:
                last_day = df.index[-1].date()
                df = df[df.index.date == last_day]
        if df.empty: return None
        return df
    except: return None

def get_dark_layout(title_text):
    return dict(
        title=dict(text=f"<b>{title_text}</b>", font=dict(color='#f5f5f7', size=16)),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis=dict(showgrid=False, gridcolor='#38383a', tickfont=dict(color='#86868b')),
        yaxis=dict(showgrid=True, gridcolor='#2c2c2e', tickfont=dict(color='#86868b'), zerolinecolor='#38383a')
    )

def plot_daily_k(df):
    if df.empty: return None
    df = df.copy()
    df['Date'] = pd.to_datetime(df['date'])
    df.set_index('Date', inplace=True)
    df = df.tail(120)
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#34c759', increasing_fillcolor='#34c759',
        decreasing_line_color='#ff3b30', decreasing_fillcolor='#ff3b30',
        name="Daily K"
    )])
    layout = get_dark_layout("6-Month Price Trend")
    layout['xaxis_rangeslider_visible'] = False
    layout['height'] = 350
    fig.update_layout(**layout)
    return fig

def plot_intraday_line(df):
    if df is None or df.empty: return None
    interval_str = "1 Min" if (df.index[1] - df.index[0]).seconds == 60 else "5 Min"
    y_min, y_max = df['Close'].min(), df['Close'].max()
    padding = (y_max - y_min) * 0.1 if y_max != y_min else y_max * 0.01
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'], mode='lines',
        line=dict(color='#0A84FF', width=2.5),
        fill='tozeroy', fillcolor='rgba(10, 132, 255, 0.1)', name='Quote'
    ))
    fig.add_hline(y=df['Open'].iloc[0], line_dash="dot", line_color="#86868b")
    layout = get_dark_layout(f"Intraday Dynamics ({interval_str})")
    layout['height'] = 350
    layout['hovermode'] = "x unified"
    layout['yaxis']['tickformat'] = '.2f'
    layout['yaxis']['range'] = [y_min - padding, y_max + padding]
    layout['xaxis']['tickformat'] = '%H:%M'
    fig.update_layout(**layout)
    return fig

market_categories = {
    "Global Macro & Risk": {
        "TAIEX (Taiwan)": "^TWII", "S&P 500 (US)": "^GSPC",
        "Dow Jones (US)": "^DJI", "Nasdaq (US)": "^IXIC",
        "SOX (Semiconductor)": "^SOX", "VIX (Volatility)": "^VIX",
        "U.S. 10Y Treasury": "^TNX", "Gold Futures": "GC=F",
        "WTI Crude Oil": "CL=F", "Bitcoin (Crypto)": "BTC-USD",
        "US Dollar Index (DXY)": "DX-Y.NYB", "USD/TWD": "TWD=X",
        "Cotton Futures": "CT=F", "BDRY (Shipping ETF)": "BDRY"
    },
    "Core Business Entities": {
        "1402 FENC": "1402", "1102 ACC": "1102", "2606 U-Ming": "2606",
        "1460 Everest": "1460", "2903 FEDS": "2903", "4904 FET": "4904", "1710 OUCC": "1710"
    },
    "Global Brand Peers (Apparel)": {
        "Nike": "NKE", "Under Armour": "UAA", "Lululemon": "LULU",
        "Adidas (ADR)": "ADDYY", "Puma (ADR)": "PUMSY", "Columbia": "COLM",
        "Gap Inc": "GAP", "Fast Retailing (ADR)": "FRCOY", "VF Corp": "VFC"
    }
}

with st.sidebar:
    st.markdown("<h3 style='color:#f5f5f7; font-weight: 600;'>Target Selection</h3>", unsafe_allow_html=True)
    selected_category = st.selectbox("Category", list(market_categories.keys()))
    options_dict = market_categories[selected_category]
    option = st.radio("Asset", list(options_dict.keys()))
    code = options_dict[option]
    
    is_tw_stock = code.isdigit()
    is_tw_index = (code == "^TWII")
    is_us_index = (code in ["^GSPC", "^DJI", "^IXIC", "^SOX", "^VIX", "^TNX"])
    is_crypto = ("BTC" in code)
    is_forex = ("=X" in code or "DX" in code)
    is_futures = ("=F" in code)
    is_us_stock = not (is_tw_stock or is_tw_index or is_us_index or is_crypto or is_forex or is_futures)
    
    if is_tw_stock or is_tw_index or code == "TWD=X": market_type = 'TW'
    elif is_crypto: market_type = 'CRYPTO'
    else: market_type = 'US'
    
    st.divider()
    status_code, status_text = check_market_status(market_type=market_type)
    st.info(f"Status: {status_text}")
    if st.button("Sync Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

real_data = {'price': 0, 'high': '-', 'low': '-', 'open': '-', 'volume': '-'}
if is_tw_stock:
    try:
        real = twstock.realtime.get(code)
        if real['success']:
            info = real['realtime']
            latest = float(info['latest_trade_price']) if info['latest_trade_price'] != '-' else 0.0
            if latest == 0.0: latest = float(info['open']) if info['open'] != '-' else 0.0
            real_data['price'] = latest
            real_data['high'] = info.get('high', '-')
            real_data['low'] = info.get('low', '-')
            real_data['open'] = info.get('open', '-')
            real_data['volume'] = info.get('accumulate_trade_volume', '0')
    except: pass
    hist_data = fetch_twse_history_proxy(code)
else:
    try:
        tk = yf.Ticker(code)
        fi = tk.fast_info
        latest = fi.last_price
        real_data['price'] = latest
        real_data['open'] = fi.open
        real_data['high'] = fi.day_high
        real_data['low'] = fi.day_low
        real_data['volume'] = f"{int(fi.last_volume):,}"
    except: pass
    hist_data = fetch_us_history(code)

df_daily = pd.DataFrame(hist_data) if hist_data else pd.DataFrame()
df_intra = get_intraday_chart_data(code, is_us_source=not is_tw_stock)
current_price = real_data['price']
if (current_price == 0 or current_price is None) and not df_daily.empty:
    current_price = df_daily.iloc[-1]['close']
    real_data['high'] = df_daily.iloc[-1]['high']
    real_data['low'] = df_daily.iloc[-1]['low']
    real_data['open'] = df_daily.iloc[-1]['open']
    vol_num = df_daily.iloc[-1]['volume']
    real_data['volume'] = f"{int(vol_num / 1000):,}" if is_tw_stock else f"{int(vol_num):,}"

prev_close = 0
if not df_daily.empty:
    if not is_tw_stock:
        try: prev_close = tk.fast_info.previous_close
        except: prev_close = df_daily.iloc[-2]['close'] if len(df_daily) > 1 else df_daily.iloc[-1]['close']
    else:
        last_date = df_daily.iloc[-1]['date']
        today_str = datetime.now().strftime('%Y-%m-%d')
        prev_close = df_daily.iloc[-2]['close'] if last_date == today_str and len(df_daily) > 1 else df_daily.iloc[-1]['close']

change = current_price - prev_close
pct = (change / prev_close) * 100 if prev_close != 0 else 0

font_color = "#34c759" if change >= 0 else "#ff3b30"
currency_symbol = "NT$" if (is_tw_stock or is_tw_index or code == "TWD=X") else "$"
unit_label = "Pts" if (is_tw_index or is_us_index or code == "DX-Y.NYB") else \
             "/ oz" if (is_futures and ("GC" in code or "SI" in code)) else \
             "/ bbl" if (is_futures and "CL" in code) else \
             "%" if code == "^TNX" else ""

st.markdown(f"""
<div style="background-color: #1c1c1e; padding: 30px; border-radius: 20px; margin-bottom: 25px; border: 1px solid #38383a; box-shadow: 0 10px 30px rgba(0,0,0,0.2);">
    <h2 style="margin:0; color:#86868b; font-size: 1.1rem; font-weight: 500; letter-spacing: 0.5px;">{option}</h2>
    <div style="display: flex; align-items: baseline; gap: 20px; margin-top: 8px;">
        <span style="font-size: 3.8rem; font-weight: 700; color: #f5f5f7; letter-spacing: -1.5px;">
           {currency_symbol.replace('NT$', '') if code != '^TNX' else ''} {current_price:,.2f} <span style="font-size: 1.2rem; color:#86868b; font-weight: 400;">{unit_label}</span>
        </span>
        <span style="font-size: 1.8rem; font-weight: 600; color: {font_color};">
             {change:+.2f} ({pct:+.2f}%)
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

hide_volume = (is_tw_index or is_us_index or is_forex)
safe_fmt = lambda x: f"{x:,.2f}" if isinstance(x, (int, float)) else x
if hide_volume:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Open", safe_fmt(real_data.get('open')))
    c2.metric("High", safe_fmt(real_data.get('high')))
    c3.metric("Low", safe_fmt(real_data.get('low')))
    c4.metric("Prev Close", f"{prev_close:,.2f}")
else:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Open", safe_fmt(real_data.get('open')))
    c2.metric("High", safe_fmt(real_data.get('high')))
    c3.metric("Low", safe_fmt(real_data.get('low')))
    c4.metric("Prev Close", f"{prev_close:,.2f}")
    c5.metric("Volume", real_data.get('volume', '-'))

st.divider()
col1, col2 = st.columns([1, 1])
with col1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    if df_intra is not None and not df_intra.empty: st.plotly_chart(plot_intraday_line(df_intra), use_container_width=True)
    else: st.info("Intraday data unavailable.")
    st.markdown('</div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    if not df_daily.empty: st.plotly_chart(plot_daily_k(df_daily), use_container_width=True)
    else: st.info("Historical data unavailable.")
    st.markdown('</div>', unsafe_allow_html=True)

update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"<div style='text-align: center; color: #86868b; font-size: 0.8rem; margin-top: 40px;'>Last synced: {update_time} (CST)</div>", unsafe_allow_html=True)
