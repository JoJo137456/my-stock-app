import streamlit as st
import twstock
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, time as dt_time
import pytz
import requests
import urllib3
import yfinance as yf
from bs4 import BeautifulSoup

# === 0. 系統層級修復 ===
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
original_request = requests.Session.request
def patched_request(self, method, url, *args, **kwargs):
    kwargs['verify'] = False
    return original_request(self, method, url, *args, **kwargs)
requests.Session.request = patched_request

# === 1. 戰情室初始化 ===
st.set_page_config(page_title="FENC Audit Department | Strategic Dashboard", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei') 

# === 淺藍系現代化登入介面 ===
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True

    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;800&family=Noto+Sans+TC:wght@500;700;900&display=swap');
        [data-testid="stSidebar"], header, [data-testid="collapsedControl"] {display: none !important;}
        
        .stApp { background-color: #F0F8FF !important; font-family: 'Poppins', 'Noto Sans TC', sans-serif !important; }
        .stApp::before { content: ''; position: fixed; bottom: -30vh; left: -15vw; width: 65vw; height: 65vw; background-color: #D6EAF8; border-radius: 50%; z-index: 0; }
        .main .block-container { z-index: 1; padding-top: 10vh !important; }
        .hero-subtitle { font-size: 16px; font-weight: 700; color: #1A1B20; margin-bottom: 15px; display: flex; align-items: center; }
        .hero-subtitle::before { content: ''; display: inline-block; width: 40px; height: 2px; background-color: #1A1B20; margin-right: 15px; }
        .hero-title-solid { font-size: 70px; font-weight: 800; color: #1A1B20; line-height: 1.1; margin-bottom: 0; letter-spacing: -2px; }
        .hero-title-outline { font-size: 55px; font-weight: 900; color: transparent; -webkit-text-stroke: 1.5px #1A1B20; line-height: 1.2; margin-top: 5px; margin-bottom: 50px; }
        .label-dashboard { background-color: #1A1B20; color: #ffffff; padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 14px; display: inline-block; }
        [data-testid="column"]:nth-of-type(3) { background: #ffffff; border-radius: 20px; padding: 40px 35px; box-shadow: 0 15px 35px rgba(0,0,0,0.04); margin-top: 20px; }
        .login-dept { font-size: 28px; color: #1A1B20; font-weight: 900; margin-bottom: 2px; }
        .login-title { font-size: 16px; font-weight: 600; color: #888888; margin-bottom: 30px; }
        .login-label { font-size: 13px; color: #888888; margin-bottom: 8px; font-weight: 600; }
        div[data-baseweb="input"] > div { border: 1px solid #E0E0E0 !important; background-color: #ffffff !important; border-radius: 8px !important; height: 52px !important; }
        button[kind="primary"] { background-color: #1A1B20 !important; color: white !important; border-radius: 8px !important; height: 50px !important; font-weight: 600 !important; }
    </style>
    """, unsafe_allow_html=True)

    col_left, spacer, col_right = st.columns([1.1, 0.2, 0.9])
    with col_left:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div class="hero-subtitle">Strategic Command</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-title-solid">Audit. Department</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-title-outline">Far Eastern Group</div>', unsafe_allow_html=True)
        st.markdown('<div class="label-dashboard">Intelligence Nexus</div>', unsafe_allow_html=True)
    with col_right:
        st.markdown('<div class="login-dept">遠東聯合稽核總部</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-title">Login Now</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-label">Customer ID</div>', unsafe_allow_html=True)
        st.text_input("", value="fenc07822", label_visibility="collapsed", key="acc_id")
        st.markdown('<div class="login-label" style="margin-top:20px;">Enter Passcode</div>', unsafe_allow_html=True)
        pwd = st.text_input("", type="password", label_visibility="collapsed", key="pwd")
        
        if st.button("Login Now ──", type="primary", use_container_width=True):
            if pwd == "AUDIT@01":
                st.session_state["password_correct"] = True
                st.rerun()
            elif pwd != "":
                st.error("Invalid credentials")
        st.markdown('<div class="it-contact" style="text-align:center; margin-top:20px; color:#888; font-size:12px;">IT Contact Curt Lee (#6855)</div>', unsafe_allow_html=True)
    return False

if not check_password(): st.stop()

# ==========================================
# === 2. 核心功能模組 (進入儀表板) ===
# ==========================================

st.markdown("""
    <style>
        html, body, [class*="css"]  { font-family: 'Microsoft JhengHei', 'Segoe UI', sans-serif !important; }
        .main-title { font-size: 2.2rem; font-weight: 700; color: #1e293b; text-align: center; margin: 1rem 0; letter-spacing: 1px;}
        .sub-title { font-size: 1rem; color: #64748b; text-align: center; margin-bottom: 2rem; }
        .chart-container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; border: 1px solid #e2e8f0; }
        .eli3-box { background: #fdfae1; padding: 20px; border-left: 5px solid #facc15; border-radius: 5px; margin-bottom: 20px; font-size: 1.05rem; line-height: 1.6; color: #422006;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">遠東集團 (Far Eastern Group)</div><div class="sub-title">聯合稽核總部 ｜ 戰略決策儀表板</div>', unsafe_allow_html=True)

def check_market_status(market_type='TW'):
    now = datetime.now(tw_tz)
    if market_type == 'CRYPTO': return "open", "🟢 數位資產 (24H 交易)"
    if market_type == 'US':
        hour = now.hour
        if 21 <= hour or hour < 5: return "open", "🟢 國際市場 (交易中)"
        else: return "closed", "🔴 國際市場 (休市/盤後)"
            
    current_time = now.time()
    is_weekend = now.weekday() >= 5
    if is_weekend: return "closed", "🔴 台股市場 (週末休市)"
    elif dt_time(9, 0) <= current_time <= dt_time(13, 35): return "open", "🟢 台股市場 (盤中即時)"
    else: return "closed", "🔴 台股市場 (盤後結算)"

# --- 資料獲取 API ---
@st.cache_data(ttl=3600) 
def fetch_twse_history_proxy(stock_code):
    try:
        data_list = []
        now = datetime.now()
        for i in range(6):
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
        hist = tk.history(period="6mo")
        data_list = [{'date': idx.strftime('%Y-%m-%d'), 'volume': float(row['Volume']), 'open': float(row['Open']), 'high': float(row['High']), 'low': float(row['Low']), 'close': float(row['Close'])} for idx, row in hist.iterrows()]
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
            if not df.empty: df = df[df.index.date == df.index[-1].date()]
        return df if not df.empty else None
    except: return None

# --- 新增：Yahoo TW 爬蟲與同業對標資料 ---
@st.cache_data(ttl=3600)
def scrape_yahoo_tw_financials(stock_code):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    data = {"revenue": [], "eps": []}
    try:
        res = requests.get(f"https://tw.stock.yahoo.com/quote/{stock_code}.TW/revenue", headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.find_all('li', class_='List(n)')[:6]:
            cols = item.find_all('div')
            if len(cols) >= 3: data["revenue"].append({"月度": cols[0].text.strip(), "單月營收 (千)": cols[1].text.strip()})
    except: pass
    
    try:
        res = requests.get(f"https://tw.stock.yahoo.com/quote/{stock_code}.TW/eps", headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.find_all('li', class_='List(n)')[:4]:
            cols = item.find_all('div')
            if len(cols) >= 3: data["eps"].append({"季度": cols[0].text.strip(), "單季EPS": cols[1].text.strip()})
    except: pass
    return data

@st.cache_data(ttl=86400)
def fetch_peer_history_for_baseline(peers):
    hist_dict = {}
    for p in peers:
        df = fetch_twse_history_proxy(p['code'])
        if df:
            temp_df = pd.DataFrame(df)[['date', 'close']]
            temp_df.rename(columns={'close': f"{p['zh']}_{p['code']}"}, inplace=True)
            hist_dict[p['code']] = temp_df
    if not hist_dict: return pd.DataFrame()
    
    main_df = list(hist_dict.values())[0]
    for code, df in list(hist_dict.items())[1:]:
        main_df = pd.merge(main_df, df, on='date', how='inner')
    return main_df

# === 3. 繪圖模組 ===
def plot_daily_k(df):
    if df.empty: return None
    df = df.copy()
    df.set_index(pd.to_datetime(df['date']), inplace=True)
    df = df.tail(120)
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], increasing_fillcolor='#ef4444', decreasing_fillcolor='#22c55e', name="日K")])
    fig.update_layout(title="<b>📊 歷史價格走勢 (近半年)</b>", xaxis_rangeslider_visible=False, height=350, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig

def plot_intraday_line(df):
    if df is None or df.empty: return None
    y_min, y_max = df['Close'].min(), df['Close'].max()
    padding = (y_max - y_min) * 0.1 if y_max != y_min else y_max * 0.01
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', line=dict(color='#0f172a', width=2.5), fill='tozeroy', fillcolor='rgba(15, 23, 42, 0.05)', name='報價'))
    fig.update_layout(title="<b>⚡ 當日分時動態</b>", height=350, margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(range=[y_min - padding, y_max + padding]))
    return fig

def plot_relative_strength(df_target, df_bench, target_name, bench_name):
    if df_target.empty or df_bench.empty: return None
    df1, df2 = df_target[['date', 'close']].tail(60).copy(), df_bench[['date', 'close']].tail(60).copy()
    merged = pd.merge(df1, df2, on='date', suffixes=('_target', '_bench'), how='inner')
    if merged.empty: return None
    merged['Target_Norm'] = (merged['close_target'] / merged['close_target'].iloc[0]) * 100
    merged['Bench_Norm'] = (merged['close_bench'] / merged['close_bench'].iloc[0]) * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=merged['date'], y=merged['Bench_Norm'], mode='lines', line=dict(color='#cbd5e1', width=2, dash='dash'), name=bench_name))
    fig.add_trace(go.Scatter(x=merged['date'], y=merged['Target_Norm'], mode='lines', line=dict(color='#2563eb', width=3), name=target_name))
    fig.update_layout(title=f"<b>🛡️ 戰略雷達：相對大盤強勢分析 (對標 {bench_name})</b>", height=350, margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig

def plot_relative_strength_base100(df, target_col):
    df = df.copy()
    df.set_index(pd.to_datetime(df['date']), inplace=True)
    df.drop(columns=['date'], inplace=True)
    normalized_df = df.div(df.iloc[0]) 
    relative_df = (normalized_df.div(normalized_df[target_col], axis=0)) * 100
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=relative_df.index, y=relative_df[target_col], mode='lines', name=f"基準: {target_col.split('_')[0]} (100)", line=dict(color='#0f172a', width=4)))
    colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
    color_idx = 0
    for col in relative_df.columns:
        if col != target_col:
            fig.add_trace(go.Scatter(x=relative_df.index, y=relative_df[col], mode='lines', name=col.split('_')[0], line=dict(width=2, color=colors[color_idx % len(colors)])))
            color_idx += 1
    fig.update_layout(title="<b>⚔️ 產業對手相對強弱對比 (Target = 100)</b>", height=350, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', hovermode="x unified")
    return fig

# === 4. 主控台邏輯 (完整保留原版選單) ===
market_categories = {
    "📈 總體經濟與大盤 (宏觀與風險指標)": {
        "🇹🇼 台灣加權指數 (TAIEX)": "^TWII", "🇺🇸 S&P 500 (標普 500 指數)": "^GSPC", "🇺🇸 Dow Jones (道瓊工業指數)": "^DJI", "🇺🇸 Nasdaq (那斯達克指數)": "^IXIC", 
        "🇺🇸 SOX (費城半導體指數)": "^SOX", "⚠️ VIX 恐慌指數 (市場風險)": "^VIX", "🏦 U.S. 10Y Treasury (實質利率)": "^TNX", "🥇 黃金期貨 (資金避險)": "GC=F", 
        "🥈 白銀期貨 (工業金屬)": "SI=F", "🛢️ WTI 原油 (能源成本)": "CL=F", "₿ 比特幣 (數位資產)": "BTC-USD", "💵 美元指數 (DXY)": "DX-Y.NYB", 
        "💱 美元兌台幣 (匯率曝險)": "TWD=X", "☁️ 棉花期貨 (紡纖原物料)": "CT=F", "🚢 BDRY 散裝航運 ETF (運價指標)": "BDRY"
    },
    "🏢 遠東集團核心事業體": {
        "🇹🇼 1402 遠東新": "1402", "🇹🇼 1102 亞泥": "1102", "🇹🇼 2606 裕民": "2606", "🇹🇼 1460 宏遠": "1460", 
        "🇹🇼 2903 遠百": "2903", "🇹🇼 4904 遠傳": "4904", "🇹🇼 1710 東聯": "1710", "🇹🇼 2845 遠東銀": "2845"
    },
    "👕 國際品牌終端 (紡織板塊對標)": {
        "🇺🇸 Nike": "NKE", "🇺🇸 Under Armour": "UAA", "🇺🇸 Lululemon": "LULU", "🇺🇸 Adidas (ADR)": "ADDYY", "🇺🇸 Puma (ADR)": "PUMSY", "🇺🇸 Columbia": "COLM", "🇺🇸 Gap Inc": "GAP", "🇺🇸 Fast Retailing (Uniqlo)": "FRCOY", "🇺🇸 VF Corp": "VFC"
    },
    "🥤 國際品牌終端 (化纖板塊對標)": {
        "🇺🇸 Coca-Cola": "KO", "🇺🇸 PepsiCo": "PEP"
    }
}

INDUSTRY_PEERS = {
    "1402": {"name": "紡織纖維 (Textiles)", "peers": [{"code": "1402", "zh": "遠東新", "en": "FENC"}, {"code": "1476", "zh": "儒鴻", "en": "Eclat"}, {"code": "1477", "zh": "聚陽", "en": "Makalot"}, {"code": "1440", "zh": "南紡", "en": "Tainan Spinning"}, {"code": "1444", "zh": "力麗", "en": "Lealea"}]},
    "1102": {"name": "水泥工業 (Cement)", "peers": [{"code": "1102", "zh": "亞泥", "en": "ACC"}, {"code": "1101", "zh": "台泥", "en": "TCC"}, {"code": "1103", "zh": "嘉泥", "en": "CHC"}, {"code": "1108", "zh": "幸福", "en": "Hsing Ta"}, {"code": "1109", "zh": "信大", "en": "Hsin Ta"}]},
    "4904": {"name": "通信網路 (Telecommunications)", "peers": [{"code": "4904", "zh": "遠傳", "en": "FET"}, {"code": "2412", "zh": "中華電", "en": "CHT"}, {"code": "3045", "zh": "台灣大", "en": "TWM"}]}
}

ELI3_MODELS = {
    "1402": "👶 **賣什麼**：我們做衣服的布料，還有裝飲料的寶特瓶唷！<br>💰 **怎麼賺錢**：把石油變成神奇的塑膠粒，再把它們變成好穿的衣服賣給大公司！<br>⚙️ **商業模式**：從最原始的原料到最後的衣服全部自己做（垂直整合）。靠著技術厲害、成本便宜賺取差價。",
    "1102": "👶 **賣什麼**：蓋房子、造橋鋪路用的灰灰粉末，叫做「水泥」！<br>💰 **怎麼賺錢**：把山上的石頭挖下來，放進超熱的大爐子裡烤，變成水泥後賣給工人。<br>⚙️ **商業模式**：水泥很重運費很貴，所以我們在很多地方蓋工廠，誰離我們近就賣給誰，並靠控制煤炭成本賺錢。",
    "4904": "👶 **賣什麼**：賣讓你的手機可以上網看影片的「隱形電波」！<br>💰 **怎麼賺錢**：每個月收爸爸媽媽的電話費和網路費。<br>⚙️ **商業模式**：花很多錢蓋高高的基地台，然後像收過路費一樣，每個月向大家收月租費，帶來穩定的現金流！"
}

with st.sidebar:
    st.header("🎯 戰略監控目標")
    selected_category = st.selectbox("板塊分類", list(market_categories.keys()))
    st.markdown("---")
    options_dict = market_categories[selected_category]
    option = st.radio("監控標的", list(options_dict.keys()))
    code = options_dict[option]
    
    is_tw_stock = code.isdigit()
    is_crypto = ("BTC" in code)
    is_forex = ("=X" in code or "DX" in code)
    is_tw_index = (code == "^TWII")
    is_us_index = (code in ["^GSPC", "^DJI", "^IXIC", "^SOX", "^VIX", "^TNX"])
    is_futures = ("=F" in code)
    is_us_stock = not (is_tw_stock or is_tw_index or is_us_index or is_crypto or is_forex or is_futures)

    market_type = 'TW' if (is_tw_stock or is_tw_index or code == "TWD=X") else ('CRYPTO' if is_crypto else 'US')
    status_code, status_text = check_market_status(market_type=market_type)
    
    st.divider()
    st.info(f"市場狀態：{status_text}")
    if st.button("🔄 同步最新報價"):
        st.cache_data.clear()
        st.rerun()

# === 5. 資料處理 ===
real_data = {'price': 0, 'high': '-', 'low': '-', 'open': '-', 'volume': '-'}

if is_tw_stock:
    try:
        real = twstock.realtime.get(code)
        if real['success']:
            info = real['realtime']
            latest = float(info['latest_trade_price']) if info['latest_trade_price'] != '-' else (float(info['open']) if info['open'] != '-' else 0.0)
            real_data.update({'price': latest, 'high': info.get('high', '-'), 'low': info.get('low', '-'), 'open': info.get('open', '-'), 'volume': info.get('accumulate_trade_volume', '0')})
    except: pass
    hist_data = fetch_twse_history_proxy(code)
else:
    try:
        tk = yf.Ticker(code)
        fi = tk.fast_info
        real_data.update({'price': fi.last_price, 'open': fi.open, 'high': fi.day_high, 'low': fi.day_low, 'volume': f"{int(fi.last_volume):,}"})
    except: pass
    hist_data = fetch_us_history(code)

df_daily = pd.DataFrame(hist_data) if hist_data else pd.DataFrame()
df_intra = get_intraday_chart_data(code, is_us_source=not is_tw_stock)

# 大盤基準對標 (Alpha/Beta)
df_bench = pd.DataFrame()
bench_name = ""
if not df_daily.empty:
    if is_tw_stock: bench_code, bench_name = "^TWII", "TAIEX (台灣加權指數)"
    elif code == "^TWII": bench_code, bench_name = "^GSPC", "S&P 500 指數"
    else: bench_code, bench_name = "^GSPC", "S&P 500 指數"
    
    if bench_code != code:
        bench_hist = fetch_us_history(bench_code)
        if bench_hist: df_bench = pd.DataFrame(bench_hist)

# Fallback 與計算漲跌
current_price = real_data['price']
if (current_price == 0 or current_price is None) and not df_daily.empty:
    current_price = df_daily.iloc[-1]['close']
    real_data.update({'high': df_daily.iloc[-1]['high'], 'low': df_daily.iloc[-1]['low'], 'open': df_daily.iloc[-1]['open']})
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

# === 6. UI 呈現 ===
bg_color = "#f8fafc"
font_color = "#dc2626" if change >= 0 else "#16a34a" 
border_color = "#fca5a5" if change >= 0 else "#86efac"
currency_symbol = "NT$" if (is_tw_stock or is_tw_index or code == "TWD=X") else "$"
unit_label = "Pts" if (is_tw_index or is_us_index or code == "DX-Y.NYB") else "/ oz" if is_futures and ("GC" in code or "SI" in code) else "/ bbl" if is_futures and "CL" in code else "%" if code == "^TNX" else ""

# A. 核心報價卡片
st.markdown(f"""
<div style="background-color: {bg_color}; padding: 25px; border-radius: 8px; margin-bottom: 25px; border-left: 6px solid {border_color};">
    <h2 style="margin:0; color:#475569; font-size: 1.1rem; font-weight: 600;">{option}</h2>
    <div style="display: flex; align-items: baseline; gap: 15px; margin-top: 8px;">
        <span style="font-size: 3.2rem; font-weight: 700; color: #0f172a; letter-spacing: -1px;">
           {currency_symbol.replace('NT$', '') if code != '^TNX' else ''} {current_price:,.2f} <span style="font-size: 1rem; color:#64748b; font-weight: 400;">{unit_label}</span>
        </span>
        <span style="font-size: 1.5rem; font-weight: 600; color: {font_color};">{change:+.2f} ({pct:+.2f}%)</span>
    </div>
</div>
""", unsafe_allow_html=True)

hide_volume = (is_tw_index or is_us_index or is_forex)
safe_fmt = lambda x: f"{x:,.2f}" if isinstance(x, (int, float)) else x

if hide_volume:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("開盤價 (Open)", safe_fmt(real_data.get('open')))
    c2.metric("最高價 (High)", safe_fmt(real_data.get('high')))
    c3.metric("最低價 (Low)", safe_fmt(real_data.get('low')))
    c4.metric("前日收盤 (Prev Close)", f"{prev_close:,.2f}")
else:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("開盤價 (Open)", safe_fmt(real_data.get('open')))
    c2.metric("最高價 (High)", safe_fmt(real_data.get('high')))
    c3.metric("最低價 (Low)", safe_fmt(real_data.get('low')))
    c4.metric("前日收盤 (Prev Close)", f"{prev_close:,.2f}")
    c5.metric("成交量 (張)" if is_tw_stock else "成交量 (Volume)", real_data.get('volume', '-'))

st.divider()

# B. 數據視覺化圖表
col1, col2 = st.columns([1, 1])
with col1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    if df_intra is not None and not df_intra.empty: st.plotly_chart(plot_intraday_line(df_intra), use_container_width=True)
    else: st.warning("暫無分時資料 (市場休市或限流)")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    if not df_daily.empty: st.plotly_chart(plot_daily_k(df_daily), use_container_width=True)
    else: st.error("暫無歷史交易資料")
    st.markdown('</div>', unsafe_allow_html=True)

# C. 戰略雷達：相對大盤強勢 (Alpha / Beta)
if not df_bench.empty and not df_daily.empty:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    rs_fig = plot_relative_strength(df_daily, df_bench, option.split(" ")[-1], bench_name)
    if rs_fig: st.plotly_chart(rs_fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# === 7. 總體經濟戰略解讀 (原版保留) ===
strategic_commentary = {
    "^TWII": {"title": "🇹🇼 台灣加權指數 (TAIEX)", "desc": "反映台灣整體資本市場動能與外資流向，為評估集團旗下台股掛牌企業之系統性估值基準。"},
    "^GSPC": {"title": "🇺🇸 S&P 500 (標普 500 指數)", "desc": "美國大型股基準，反映全球總體經濟的健康度。"},
    "^SOX": {"title": "🇺🇸 SOX (費城半導體指數)", "desc": "全球半導體景氣核心指標。其強弱決定台股的「資金排擠效應」。"},
    "^VIX": {"title": "⚠️ VIX 恐慌指數 (市場波動率)", "desc": "衡量總體經濟避險情緒與流動性壓力的關鍵指標。"},
    "CT=F": {"title": "☁️ Cotton Futures (棉花期貨)", "desc": "牽動紡織事業板塊之核心進貨成本與毛利率表現。"}
}

if code in strategic_commentary:
    st.markdown("### 📊 宏觀指標與戰略洞察")
    st.info(f"**{strategic_commentary[code]['title']}**：{strategic_commentary[code]['desc']}")

# ==========================================
# === 8. 新功能：企業基本面與產業戰略解析 (僅限集團事業體) ===
# ==========================================
if is_tw_stock and code in INDUSTRY_PEERS:
    st.divider()
    st.markdown(f"### 📈 企業基本面與產業戰略解析：{option.split(' ')[-1]}")

    if code in ELI3_MODELS:
        st.markdown(f'<div class="eli3-box"><b>🧸 3歲小孩也懂的商業模式：</b><br>{ELI3_MODELS[code]}</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📊 營收與獲利 (Yahoo TW 同步)", "⚔️ 產業同行對標 (Base 100)"])

    with tab1:
        scraped_data = scrape_yahoo_tw_financials(code)
        col_rev, col_eps = st.columns(2)
        with col_rev:
            st.markdown("#### 📅 單月營收追蹤")
            if scraped_data["revenue"]: st.dataframe(pd.DataFrame(scraped_data["revenue"]), use_container_width=True, hide_index=True)
        with col_eps:
            st.markdown("#### 💰 單季 EPS (每股盈餘)")
            if scraped_data["eps"]: st.dataframe(pd.DataFrame(scraped_data["eps"]), use_container_width=True, hide_index=True)

    with tab2:
        peer_info = INDUSTRY_PEERS[code]
        st.markdown(f"**目標賽道：{peer_info['name']}**")
        st.caption("觀測名單：" + " | ".join([f"{p['zh']} ({p['en']})" for p in peer_info['peers']]))
        
        target_col_name = next((f"{p['zh']}_{p['code']}" for p in peer_info['peers'] if p['code'] == code), None)
        df_peers_hist = fetch_peer_history_for_baseline(peer_info['peers'])
        
        if not df_peers_hist.empty and target_col_name:
            st.plotly_chart(plot_relative_strength_base100(df_peers_hist, target_col_name), use_container_width=True)

update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f'<div style="text-align:center; color:#94a3b8; font-size:0.8rem; margin-top:3rem;">系統更新時間：{update_time} ｜ 資料來源：TWSE, Yahoo Finance</div>', unsafe_allow_html=True)
