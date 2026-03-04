import streamlit as st
import twstock
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, time as dt_time
import pytz
import requests
import urllib3
import yfinance as yf

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

# === 淺藍系現代化登入介面 ===
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True

    # 注入 Google 字體與全版 CSS (包含 Noto Sans TC 以支援繁體中文設計)
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;800&family=Noto+Sans+TC:wght@500;700;900&display=swap');

        /* 隱藏預設元素 */
        [data-testid="stSidebar"], header, [data-testid="collapsedControl"] {display: none !important;}
        
        /* 全域背景設定 - 淺藍色系 */
        .stApp {
            background-color: #F0F8FF !important; 
            font-family: 'Poppins', 'Noto Sans TC', sans-serif !important;
        }
        
        /* 左下角的巨大圓弧色塊 - 柔和的藍色 */
        .stApp::before {
            content: '';
            position: fixed;
            bottom: -30vh;
            left: -15vw;
            width: 65vw;
            height: 65vw;
            background-color: #D6EAF8; 
            border-radius: 50%;
            z-index: 0;
        }

        /* 將內容層次推至最上層 */
        .main .block-container {
            z-index: 1;
            padding-top: 10vh !important;
        }

        /* === 左側文字排版 === */
        .hero-subtitle {
            font-size: 16px;
            font-weight: 700;
            color: #1A1B20;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            letter-spacing: 0.5px;
        }
        .hero-subtitle::before {
            content: '';
            display: inline-block;
            width: 40px;
            height: 2px;
            background-color: #1A1B20;
            margin-right: 15px;
        }
        .hero-title-solid {
            font-size: 80px;
            font-weight: 800;
            color: #1A1B20;
            line-height: 1.1;
            margin-bottom: 0;
            letter-spacing: -2px;
        }
        
        /* 強化的輪廓字體設計 */
        .hero-title-outline {
            font-size: 55px; 
            font-weight: 900;
            color: transparent;
            -webkit-text-stroke: 1.5px #1A1B20;
            line-height: 1.2;
            margin-top: 5px;
            margin-bottom: 50px;
            letter-spacing: 1px;
        }
        
        /* 左側 Dashboard 標籤 (純視覺，無點擊效果) */
        .label-dashboard {
            background-color: #1A1B20;
            color: #ffffff;
            padding: 14px 32px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            display: inline-block;
            cursor: default; 
            letter-spacing: 1px;
        }

        /* === 右側白底登入卡片 === */
        [data-testid="column"]:nth-of-type(3) {
            background: #ffffff;
            border-radius: 20px;
            padding: 40px 35px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.04);
            margin-top: 20px;
        }
        
        /* 視覺焦點：巨大的中文部門標題 */
        .login-dept {
            font-size: 28px;
            color: #1A1B20;
            font-weight: 900;
            margin-bottom: 2px;
            letter-spacing: 1.5px;
        }
        /* 弱化的 Login Now 副標題 */
        .login-title {
            font-size: 16px;
            font-weight: 600;
            color: #888888;
            margin-bottom: 30px;
        }
        .login-label {
            font-size: 13px;
            color: #888888;
            margin-bottom: 8px;
            font-weight: 600;
        }
        
        /* 覆寫 Streamlit 輸入框外觀 */
        div[data-baseweb="input"] > div {
            border: 1px solid #E0E0E0 !important;
            background-color: #ffffff !important;
            border-radius: 8px !important;
            height: 52px !important;
            box-shadow: none !important;
        }
        div[data-baseweb="input"] > div:hover { border-color: #1A1B20 !important; }
        div[data-baseweb="input"]:focus-within > div { border: 1.5px solid #1A1B20 !important; }
        
        div[data-baseweb="input"] input {
            color: #1A1B20 !important;
            padding: 12px 16px !important;
            font-size: 15px !important;
            font-weight: 500 !important;
        }
        
        /* 條款文字 */
        .terms-text {
            font-size: 12px;
            color: #A0A0A0;
            margin: 20px 0;
            font-weight: 500;
        }
        .terms-text a { color: #A0A0A0; text-decoration: underline; }

        /* Login 按鈕 */
        button[kind="primary"] {
            background-color: #1A1B20 !important;
            color: white !important;
            border-radius: 8px !important;
            height: 50px !important;
            font-weight: 600 !important;
            padding: 0 35px !important;
            border: none !important;
            letter-spacing: 0.5px;
        }
        button[kind="primary"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        /* IT Contact 聯絡資訊 */
        .it-contact {
            margin-top: 25px;
            text-align: center;
            font-size: 12.5px;
            color: #888888;
            font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)

    # 頁面對齊佈局 (左、中、右)
    col_left, spacer, col_right = st.columns([1.1, 0.2, 0.9])
    
    with col_left:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div class="hero-subtitle">Strategic Command</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-title-solid">Audit. HQ</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-title-outline">Far Eastern Group</div>', unsafe_allow_html=True)
        st.markdown('<div class="label-dashboard">Intelligence Nexus</div>', unsafe_allow_html=True)
        
    with col_right:
        st.markdown('<div class="login-dept">遠東聯合稽核總部</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-title">Login Now</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="login-label">Customer ID</div>', unsafe_allow_html=True)
        st.text_input("", value="fenc07822", label_visibility="collapsed", key="acc_id")
        
        st.markdown('<div class="login-label" style="margin-top:20px;">Enter Passcode</div>', unsafe_allow_html=True)
        pwd = st.text_input("", type="password", label_visibility="collapsed", key="pwd")
        
        st.markdown('<div class="terms-text">By login, you agree to our <a href="#">Terms & Conditions</a></div>', unsafe_allow_html=True)
        
        btn_col, link_col = st.columns([1, 1])
        with btn_col:
            if st.button("Login Now ──", type="primary", use_container_width=True):
                if pwd == "AUDIT@01":
                    st.session_state["password_correct"] = True
                    st.rerun()
                elif pwd != "":
                    st.error("Invalid credentials")
        with link_col:
            st.markdown('<div style="text-align: right; padding-top: 15px;"><a href="#" style="color: #888; font-size: 13px; font-weight: 600; text-decoration: underline;">Forgot Passcode</a></div>', unsafe_allow_html=True)
        
        st.markdown('<div class="it-contact">IT Contact Curt Lee (#6855)</div>', unsafe_allow_html=True)

    return False

if not check_password():
    st.stop()

# === 以下為主儀表板程式碼 ===
st.markdown("""
    <style>
        .stApp { background: #000000 !important; color: #f5f5f7 !important; }
        .stApp::before { display: none !important; } 
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
        fill='tozeroy', fillcolor='rgba(10, 132,
