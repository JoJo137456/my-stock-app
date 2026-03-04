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

# === 強化版 SCADA 工業風登入介面 ===
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
            background: linear-gradient(rgba(0,0,0,0.78), rgba(0,0,0,0.88));
            z-index: -1;
        }}
        </style>
        """
        st.markdown(bg_css, unsafe_allow_html=True)

    # ────────────────────────────────────────────────
    #   最終強化版：超強霓虹 + 全透明無框輸入 + 底部發光線
    # ────────────────────────────────────────────────
    st.markdown("""
    <style>
        [data-testid="stSidebar"], header, [data-testid="collapsedControl"] {display: none !important;}
        
        /* Card */
        .scada-card {
            background: rgba(10, 12, 18, 0.95);
            backdrop-filter: blur(30px);
            border: 2px solid #00ff9f;
            border-radius: 22px;
            padding: 75px 65px 65px;
            max-width: 480px;
            margin: 80px auto 50px;
            box-shadow: 0 0 60px rgba(0, 255, 159, 0.3), 0 35px 80px rgba(0,0,0,0.9);
        }
        
        /* 超強霓虹標題 */
        .scada-title {
            font-size: 48px;
            font-weight: 900;
            color: #ffffff;
            text-align: center;
            letter-spacing: 5px;
            margin-bottom: 8px;
            text-shadow: 0 0 25px #00ff9f, 0 0 50px #00ff9f, 0 0 75px #00ff9f, 0 0 100px #00ff9f;
        }
        
        .scada-subtitle {
            font-size: 18px;
            color: #b0ffe0;
            text-align: center;
            margin-bottom: 60px;
            font-weight: 500;
            text-shadow: 0 0 18px #00ff9f;
        }
        
        /* 極致霓虹標籤 */
        .scada-label {
            font-size: 15px;
            font-weight: 900;
            color: #00ff9f;
            margin: 32px 0 10px 0;
            letter-spacing: 4px;
            text-transform: uppercase;
            display: block;
            text-align: center;
            text-shadow: 0 0 20px #00ff9f, 0 0 40px #00ff9f, 0 0 60px #00ff9f, 0 0 80px #00ff9f;
        }
        
        /* 全透明 + 僅底部發光線輸入框 */
        div[data-baseweb="input"] > div,
        div[data-baseweb="input"] > div > div {
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            border-bottom: 2px solid rgba(0, 255, 159, 0.4) !important;
            transition: all 0.3s ease;
        }
        
        div[data-baseweb="input"] input {
            color: #ffffff !important;
            font-size: 20px !important;
            font-weight: 500 !important;
            text-align: center !important;
            padding: 0 !important;
            height: 50px !important;
            caret-color: #00ff9f !important;
        }
        
        /* 強制置中 ACCOUNT ID */
        input[value="Audit_HQ_Admin"] {
            padding: 0 !important;
            text-align: center !important;
        }
        
        /* 隱藏清除按鈕 (X) */
        div[data-baseweb="input"] button {
            display: none !important;
        }
        
        /* 聚焦時超強霓虹底線 */
        div[data-baseweb="input"]:focus-within > div {
            border-bottom-color: #00ff9f !important;
            box-shadow: 0 6px 40px rgba(0, 255, 159, 0.65) !important;
            border-bottom-width: 3.5px !important;
        }
        
        /* Sign In 按鈕 */
        button[kind="primary"] {
            background: linear-gradient(90deg, #00c0ff, #0088ff) !important;
            color: #ffffff !important;
            font-size: 20px !important;
            font-weight: 800 !important;
            height: 64px !important;
            border-radius: 16px !important;
            margin-top: 45px;
            text-transform: uppercase;
            letter-spacing: 2.5px;
            border: none !important;
        }
        button[kind="primary"]:hover {
            background: linear-gradient(90deg, #00ff9f, #00e0ff) !important;
            box-shadow: 0 0 50px rgba(0, 255, 159, 0.8);
            transform: scale(1.05);
        }
        
        /* 底部超發光連結 */
        .scada-footer {
            text-align: center;
            margin-top: 55px;
            font-size: 15px;
            color: #98e8c8;
        }
        .scada-footer a {
            color: #00ff9f;
            text-decoration: none;
            font-weight: 700;
            text-shadow: 0 0 18px #00ff9f, 0 0 36px #00ff9f;
            transition: all 0.25s;
        }
        .scada-footer a:hover {
            text-shadow: 0 0 30px #00ff9f, 0 0 60px #00ff9f;
            color: #33ffcc;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<br><br><br><br><br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        with st.container():
            st.markdown('<div class="scada-card">', unsafe_allow_html=True)
            
            st.markdown('<div class="scada-title">AUDIT HQ</div>', unsafe_allow_html=True)
            st.markdown('<div class="scada-subtitle">FENC Corporate Control Access</div>', unsafe_allow_html=True)
            
            # ORGANIZATION - 靜態文字
            st.markdown('<span class="scada-label">ORGANIZATION</span>', unsafe_allow_html=True)
            st.markdown('<div style="text-align:center; color:#ffffff; font-size:20px; font-weight:700; margin-bottom:40px; letter-spacing:1px;">Far Eastern New Century (FENC)</div>', unsafe_allow_html=True)
            
            # ACCOUNT ID - 禁用 + 置中
            st.markdown('<span class="scada-label">ACCOUNT ID</span>', unsafe_allow_html=True)
            st.text_input("", value="Audit_HQ_Admin", label_visibility="collapsed", key="acct_input", disabled=True)
            
            # PASSWORD
            st.markdown('<span class="scada-label">PASSWORD</span>', unsafe_allow_html=True)
            pwd = st.text_input("", type="password", label_visibility="collapsed", key="pwd_input")
            
            if st.button("SIGN IN", type="primary", use_container_width=True):
                if pwd == "AUDIT@01":
                    st.session_state["password_correct"] = True
                    st.rerun()
                elif pwd != "":
                    st.error("❌ ACCESS DENIED — Invalid credentials")
            
            st.markdown("""
            <div class="scada-footer">
                <a href="#">Forgot Password</a>  •  <a href="#">IT Support (ext. 6855)</a>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

    return False

if not check_password():
    st.stop()

# ────────────────────────────────────────────────
#   以下為原本的主儀表板內容（保持不變）
# ────────────────────────────────────────────────

st.markdown("""
    <style>
        .stApp { background: #000000 !important; color: #f5f5f7 !important; }
        .main-title { font-size: 2.8rem; font-weight: 700; color: #f5f5f7; text-align: center; margin: 2rem 0 1rem; letter-spacing: 1.2px;}
        .sub-title { font-size: 1.2rem; color: #86868b; text-align: center; margin-bottom: 3rem; font-weight: 400;}
        .chart-container {
            background: #1c1c1e; padding: 28px; border-radius: 22px;
            margin-bottom: 28px; border: 1px solid #38383a;
        }
        div[data-testid="metric-container"] {
            background-color: #1c1c1e; border: 1px solid #38383a; padding: 18px;
            border-radius: 18px; text-align: center;
        }
        div[data-testid="metric-container"] > div { color: #f5f5f7 !important; }
        div[data-testid="metric-container"] label { color: #86868b !important; font-weight: 500 !important; font-size: 0.9rem !important; text-transform: uppercase;}
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

# ── 這裡可以繼續放你原本的儀表板內容，例如選股、圖表顯示等 ──
# 例如：
# st.write("登入成功！歡迎使用 FENC Audit HQ")
# ... 你的股票選擇、圖表呈現邏輯 ...

st.info("登入成功！Strategic Control Center 已啟動", icon="🛡️")
