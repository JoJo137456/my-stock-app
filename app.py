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

# === 1.5 Security & Authentication (Solid Apple Dark Mode UI) ===
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    # Load background image (bg.jpg)
    if os.path.exists('bg.jpg'):
        with open('bg.jpg', 'rb') as f:
            encoded_bg = base64.b64encode(f.read()).decode()
        bg_css = f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded_bg}") !important;
            background-size: cover !important;
            background-position: center !important;
            background-repeat: no-repeat !important;
        }}
        </style>
        """
        st.markdown(bg_css, unsafe_allow_html=True)
        
    st.markdown(
        """
        <style>
            /* Apply Apple's native font stack globally */
            html, body, [class*="css"] { 
                font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important; 
            }
            [data-testid="stSidebar"] {display: none;}
            [data-testid="collapsedControl"] {display: none;}
            header {visibility: hidden;}
            
            /* 1. Bulletproof Dark Container (防彈級太空灰底框) */
            [data-testid="stVerticalBlockBorderWrapper"] {
                background-color: rgba(28, 28, 30, 0.95) !important; /* iOS 系統級深灰色，95%不透明 */
                border-radius: 20px !important;
                border: 1px solid rgba(255, 255, 255, 0.15) !important;
                box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8) !important;
                padding: 40px !important;
            }
            
            /* 2. Bulletproof Input Fields (強制覆寫輸入框為深灰底、白字) */
            input[type="text"], input[type="password"], div[data-baseweb="select"] > div {
                background-color: #2C2C2E !important; 
                color: #FFFFFF !important;
                border: 1px solid #3A3A3C !important;
                border-radius: 10px !important;
                font-size: 1.05rem !important;
                font-weight: 500 !important;
                -webkit-text-fill-color: #FFFFFF !important; /* 強制文字填色為白 */
            }
            div[data-baseweb="select"] span {
                color: #FFFFFF !important;
            }
            
            /* 輸入框點擊時的藍色光暈 */
            div[data-baseweb="input"] > div:focus-within, div[data-baseweb="select"] > div:focus-within {
                border: 1px solid #0A84FF !important;
            }
            
            /* 3. Apple-style Primary Button (白色圓角按鈕) */
            button[kind="primary"] {
                background-color: #FFFFFF !important; 
                color: #000000 !important; 
                font-weight: 700 !important;
                font-size: 1.1rem !important;
                border: none !important;
                border-radius: 20px !important;
                padding: 12px !important;
                transition: all 0.2s ease !important;
            }
            button[kind="primary"]:hover {
                background-color: #E5E5EA !important;
                transform: scale(1.02);
            }
            
            /* Custom minimalist labels */
            .apple-label {
                font-size: 0.75rem;
                font-weight: 600;
                letter-spacing: 0.1em;
                color: #86868B;
                text-transform: uppercase;
                margin-bottom: 8px;
                margin-top: 16px;
                display: block;
            }
        </style>
        """, unsafe_allow_html=True
    )

    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1]) 
    
    with col2:
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center; color: #F5F5F7; font-weight: 700; margin-bottom: 30px; letter-spacing: 1px; font-size: 2.2rem;'>Audit HQ Portal</h2>", unsafe_allow_html=True)
            
            st.markdown("<span class='apple-label'>Organization</span>", unsafe_allow_html=True)
            st.selectbox("company", ["Far Eastern New Century (FENC)"], label_visibility="collapsed")
            
            st.markdown("<span class='apple-label'>Account ID</span>", unsafe_allow_html=True)
            st.text_input("account", value="Audit_HQ_Admin", label_visibility="collapsed")
            
            st.markdown("<span class='apple-label'>Password</span>", unsafe_allow_html=True)
            pwd = st.text_input("password", type="password", label_visibility="collapsed")
            
            st.markdown("""
                <div style='font-size: 0.8rem; color: #86868B; margin-top: 16px; margin-bottom: 30px; line-height: 1.5; text-align: center; font-weight: 400;'>
                Use your corporate PC/Email credentials.<br>
                For plant operations, use the leave/overtime password.
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("Sign In", type="primary", use_container_width=True):
                if pwd == "AUDIT@01":
                    st.session_state["password_correct"] = True
                    st.rerun()
                elif pwd != "":
                    st.error("Authentication failed. Please check your credentials.")
            
            st.markdown("""
                <div style='display: flex; justify-content: center; gap: 20px; margin-top: 25px;'>
                    <a href='#' style='color: #0A84FF; font-size: 0.85rem; text-decoration: none;'>Forgot Password?</a>
                    <span style='color: #424245;'>|</span>
                    <a href='#' style='color: #0A84FF; font-size: 0.85rem; text-decoration: none;'>Contact Support (Ext. 6855)</a>
                </div>
            """, unsafe_allow_html=True)

    return False

if not check_password():
    st.stop()


# === 2. Core Dashboard Module ===
st.markdown("""
    <style>
        .stApp { background: #000000 !important; color: #f5f5f7 !important; }
        .main-title { font-size: 2.5rem; font-weight: 700; color: #f5f5f7; text-align: center; margin: 1rem 0; letter-spacing: 1px;}
        .sub-title { font-size: 1.1rem; color: #86868b; text-align: center; margin-bottom: 2rem; font-weight: 400;}
        .chart-container { 
            background: #1c1c1e; padding: 20px; border-radius: 18px; 
            margin-bottom: 20px; border: 1px solid #38383a; 
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

# === 3. Plotting Module ===
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

# === 4. Dashboard Controller ===
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

# === 5. Data Processing ===
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

# === 6. UI Presentation ===
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
