import streamlit as st
import twstock
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import pytz
import requests
import urllib3
import yfinance as yf
import numpy as np

# === 0. 系統層級修復 ===
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
original_request = requests.Session.request

def patched_request(self, method, url, *args, **kwargs):
    kwargs['verify'] = False
    return original_request(self, method, url, *args, **kwargs)

requests.Session.request = patched_request

# === 1. 戰情室初始化 ===
st.set_page_config(page_title="FENC Audit Department | Executive Dashboard", layout="wide", initial_sidebar_state="expanded")
tw_tz = pytz.timezone('Asia/Taipei')

# === 登入介面 ===
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True
        
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;800&family=Noto+Sans+TC:wght@300;400;500;700;800&display=swap');
        [data-testid="stSidebar"], header, [data-testid="collapsedControl"] {display: none !important;}
        .stApp { background-color: #F0F8FF !important; font-family: 'Poppins', 'Noto Sans TC', sans-serif !important; }
        .hero-title-solid { font-size: 70px; font-weight: 800; color: #1A1A20; line-height: 1.1; margin-bottom: 0; letter-spacing: -2px; }
        .hero-title-outline { font-size: 55px; font-weight: 900; color: transparent; -webkit-text-stroke: 1.5px #1A1A20; line-height: 1.2; margin-top: 5px; margin-bottom: 50px; }
        .label-dashboard { background-color: #1A1B20; color: #ffffff; padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 14px; display: inline-block; }
    </style>
    """, unsafe_allow_html=True)
    
    col_left, spacer, col_right = st.columns([1.1, 0.2, 0.9])
    with col_left:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div class="hero-title-solid">Audit. Department</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-title-outline">Far Eastern Group</div>', unsafe_allow_html=True)
        st.markdown('<div class="label-dashboard">Executive Intelligence</div>', unsafe_allow_html=True)
    with col_right:
        st.markdown('<div style="font-size: 28px; color: #1A1B20; font-weight: 900; margin-bottom: 2px;">遠東聯合稽核總部</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size: 16px; font-weight: 600; color: #888888; margin-bottom: 30px;">Executive Login</div>', unsafe_allow_html=True)
        st.text_input("Customer ID", value="fenc07822", label_visibility="collapsed", key="acc_id")
        pwd = st.text_input("Passcode", type="password", label_visibility="collapsed", key="pwd")
        if st.button("Secure Login ──", type="primary", use_container_width=True):
            if pwd == "AUDIT@01":
                st.session_state["password_correct"] = True
                st.rerun()
            elif pwd != "":
                st.error("Invalid credentials")
    return False

if not check_password(): 
    st.stop()

# === 2. 現代化設計樣式 ===
st.markdown("""
<style>
    html, body, [class*="css"] { font-family: 'Noto Sans TC', 'Microsoft JhengHei', sans-serif !important; }
    .main-title { font-size: 2.2rem; font-weight: 800; color: #1e293b; text-align: center; margin: 1rem 0; letter-spacing: 1px;}
    .sub-title { font-size: 1rem; color: #64748b; text-align: center; margin-bottom: 2rem; font-weight: 500;}
    .definition-box { background: #ffffff; padding: 28px 32px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 6px 20px rgba(0,0,0,0.035); margin-bottom: 32px; }
    .definition-text { font-size: 15.8px; line-height: 1.85; color: #334155; padding-left: 22px; border-left: 4px solid #3b82f6; font-weight: 500; }
    
    /* 修正後的多期間報酬率 CSS */
    .returns-container { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 10px; margin-bottom: 24px; }
    .return-card { flex: 1; min-width: 100px; background-color: #ffffff; padding: 16px 10px; border-radius: 10px; text-align: center; box-shadow: 0 2px 6px rgba(0,0,0,0.04); border: 1px solid #e2e8f0; transition: transform 0.2s ease; }
    .return-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
    .return-label { font-size: 13px; color: #64748b; margin-bottom: 6px; font-weight: 500; }
    .return-value { font-size: 20px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)
st.markdown('<div class="main-title">遠東集團 (Far Eastern Group)</div><div class="sub-title">聯合稽核總部 ｜ 戰略決策儀表板</div>', unsafe_allow_html=True)

# === 3. 核心資料擷取函式 ===
@st.cache_data(ttl=3600)
def fetch_twse_history_proxy(stock_code):
    try:
        data_list = []
        now = datetime.now()
        for i in range(12):
            target_date = (now.replace(day=1) - pd.DateOffset(months=i)).strftime('%Y%m01')
            url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={target_date}&stockNo={stock_code}"
            r = requests.get(url).json()
            if r['stat'] == 'OK':
                for row in r['data']:
                    parts = row[0].split('/')
                    date_iso = f"{int(parts[0])+1911}-{parts[1]}-{parts[2]}"
                    def tf(s): return float(s.replace(',', '')) if s != '--' else 0.0
                    data_list.append({'date': date_iso, 'volume': tf(row[1]), 'open': tf(row[3]), 'high': tf(row[4]), 'low': tf(row[5]), 'close': tf(row[6])})
        return sorted(data_list, key=lambda x: x['date'])
    except: return None

@st.cache_data(ttl=3600)
def fetch_us_history(ticker_symbol):
    try:
        tk = yf.Ticker(ticker_symbol)
        hist = tk.history(period="1y")
        return [{'date': idx.strftime('%Y-%m-%d'), 'volume': float(row['Volume']), 'open': float(row['Open']), 'high': float(row['High']), 'low': float(row['Low']), 'close': float(row['Close'])} for idx, row in hist.iterrows()]
    except: return None

@st.cache_data(ttl=300)
def get_intraday_chart_data(stock_code, is_us_source=False):
    try:
        ticker = yf.Ticker(stock_code if is_us_source else f"{stock_code}.TW")
        df = ticker.history(period="1d", interval="1m")
        if df.empty:
            df = ticker.history(period="5d", interval="5m")
            if not df.empty: df = df[df.index.date == df.index[-1].date()]
        return df if not df.empty else None
    except: return None

def calculate_period_returns(df_daily, current_price):
    if df_daily.empty or len(df_daily) < 2:
        return {}
    df = df_daily.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    current_close = current_price if current_price and current_price != 0 else df['close'].iloc[-1]
    periods = {"近3天": 3, "近1週": 5, "近2週": 10, "近1月": 21, "近1季": 63, "近半年": 126, "近1年": 252}
    returns = {}
    for label, days in periods.items():
        if len(df) > days:
            past_close = df.iloc[len(df)-1-days]['close']
            ret = ((current_close - past_close) / past_close) * 100 if past_close != 0 else 0
            returns[label] = round(ret, 2)
        else:
            returns[label] = "N/A"
    return returns

# ⚠️ 請在此處貼上你原本的其他函式 (get_resilient_financials, calculate_ai_audit_score, plot_daily_k 等)

# === 4. 標的定義庫 ===
# ⚠️ 請將你完整的 TARGET_DEFINITIONS 字典貼回這裡
TARGET_DEFINITIONS = {
    "範例標的": "這是一個範例說明，請替換成真實的定義庫內容。"
}

# === 5. 側邊欄與資料抓取 ===
# ⚠️ 請將你完整的 market_categories 字典貼回這裡
market_categories = {
    "📈 總體經濟與大盤 (宏觀指標)": { "台灣加權指數": "^TWII" },
    "🏢 遠東集團核心事業體": { "遠東新": "1402" }
}

with st.sidebar:
    st.header("🎯 戰略監控目標")
    selected_category = st.selectbox("板塊分類", list(market_categories.keys()))
    st.markdown("---")
    options_dict = market_categories[selected_category]
    option = st.radio("監控標的", list(options_dict.keys()))
    code = options_dict[option]
    is_tw_stock = code.isdigit()

# ⚠️ 請在此處貼上你原本的 real_data、hist_data、df_daily、df_intra、current_price、change、pct 計算程式碼
# 為了讓此範例不報錯，下方提供簡單的預設值，實裝時請刪除並換回你的邏輯：
current_price, change, pct = 0.0, 0.0, 0.0
df_daily = pd.DataFrame() 
df_intra = pd.DataFrame()

# === 6. 介面渲染：股價與定義 ===
st.markdown(f"""
<div style="background-color: #ffffff; padding: 25px; border-radius: 8px; margin-bottom: 25px; border-left: 6px solid {'#ef4444' if change >= 0 else '#22c55e'}; box-shadow: 0 2px 5px rgba(0,0,0,0.03);">
    <h2 style="margin:0; color:#475569; font-size: 1.25rem; font-weight: 800;">{option}</h2>
    <div style="display: flex; align-items: baseline; gap: 15px; margin-top: 8px;">
        <span style="font-size: 3.2rem; font-weight: 800; color: #0f172a; letter-spacing: -1px;">
            {"NT$" if is_tw_stock else ""} {current_price:,.2f}
        </span>
        <span style="font-size: 1.5rem; font-weight: 700; color: {'#ef4444' if change >= 0 else '#22c55e'};">{change:+.2f} ({pct:+.2f}%)</span>
    </div>
</div>
""", unsafe_allow_html=True)

if option in TARGET_DEFINITIONS:
    exp_text = TARGET_DEFINITIONS[option]
    st.markdown(f"""
    <div class="definition-box">
        <div class="definition-text">{exp_text}</div>
    </div>
    """, unsafe_allow_html=True)

# === 7. 修正後的多期間報酬率卡片 ===
period_returns = calculate_period_returns(df_daily, current_price)
if period_returns:
    st.markdown("### 📅 多期間報酬率指標 (Multi-Period Returns)")
    return_html = '<div class="returns-container">'
    for label, ret in period_returns.items():
        if ret == "N/A":
            color = "#94a3b8"
            disp = "N/A"
        else:
            color = "#ef4444" if ret >= 0 else "#22c55e"
            disp = f"{ret:+.2f}%"
        return_html += f'<div class="return-card"><div class="return-label">{label}</div><div class="return-value" style="color:{color};">{disp}</div></div>'
    return_html += '</div>'
    st.markdown(return_html, unsafe_allow_html=True)

# === 8. 警示與圖表 (請將原本的內容補回) ===
col1, col2 = st.columns([1, 1])
# with col1: ... (你的盤中折線圖)
# with col2: ... (你的日K線圖)

# === 9. 下半部財務戰情室 (請將原本的內容補回) ===

update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f'<div style="text-align:center; color:#94a3b8; font-size:0.8rem; margin-top:3rem;">系統更新時間：{update_time} ｜ 資料來源：TWSE, Yahoo Finance, FinMind</div>', unsafe_allow_html=True)
