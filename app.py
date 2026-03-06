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
import re

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
# === 2. 核心功能與 UI 美化 ===
# ==========================================
st.markdown("""
    <style>
        html, body, [class*="css"]  { font-family: 'Microsoft JhengHei', 'Segoe UI', sans-serif !important; }
        .main-title { font-size: 2.2rem; font-weight: 700; color: #1e293b; text-align: center; margin: 1rem 0; letter-spacing: 1px;}
        .sub-title { font-size: 1rem; color: #64748b; text-align: center; margin-bottom: 2rem; }
        .chart-container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; border: 1px solid #e2e8f0; }
        .fin-card { background: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; text-align: center; }
        .fin-card h4 { margin: 0; color: #64748b; font-size: 0.9rem; font-weight: 500; }
        .fin-card h2 { margin: 5px 0 0 0; color: #0f172a; font-size: 1.5rem; font-weight: 700; }
        .eli3-box { background: #fdfae1; padding: 20px; border-left: 5px solid #facc15; border-radius: 5px; margin-bottom: 20px; font-size: 1.05rem; line-height: 1.6; color: #422006;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">遠東集團 (Far Eastern Group)</div><div class="sub-title">聯合稽核總部 ｜ 戰略決策儀表板</div>', unsafe_allow_html=True)

# === API 與資料抓取模組 ===
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
def scrape_yahoo_tw_financials(stock_code):
    """強行爬取 Yahoo TW 的單月營收與單季 EPS"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
    data = {"revenue": [], "eps": []}
    
    # 爬取單月營收
    try:
        rev_url = f"https://tw.stock.yahoo.com/quote/{stock_code}.TW/revenue"
        res = requests.get(rev_url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 尋找包含資料的清單項目 (Yahoo TW 結構經常變動，這裡抓取常見的 div 網格)
        list_items = soup.find_all('li', class_='List(n)')
        for item in list_items[:6]: # 取近6個月
            cols = item.find_all('div')
            if len(cols) >= 3:
                month = cols[0].text.strip()
                rev = cols[1].text.strip()
                data["revenue"].append({"月度": month, "單月營收 (千)": rev})
    except: pass
    
    # 爬取 EPS
    try:
        eps_url = f"https://tw.stock.yahoo.com/quote/{stock_code}.TW/eps"
        res = requests.get(eps_url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        list_items = soup.find_all('li', class_='List(n)')
        for item in list_items[:4]: # 取近4季
            cols = item.find_all('div')
            if len(cols) >= 3:
                quarter = cols[0].text.strip()
                eps = cols[1].text.strip()
                data["eps"].append({"季度": quarter, "單季EPS": eps})
    except: pass
    return data

@st.cache_data(ttl=300) 
def get_intraday_chart_data(stock_code, is_us_source=False):
    try:
        tk = yf.Ticker(stock_code if is_us_source else f"{stock_code}.TW")
        df = tk.history(period="1d", interval="1m")
        if df.empty:
            df = tk.history(period="5d", interval="5m")
            if not df.empty: df = df[df.index.date == df.index[-1].date()]
        return df if not df.empty else None
    except: return None

# === 同業競爭對標清單 (中英雙語 + 基準定義) ===
INDUSTRY_PEERS = {
    "1402": {
        "name": "紡織纖維 (Textiles)", 
        "peers": [
            {"code": "1402", "zh": "遠東新", "en": "FENC"},
            {"code": "1476", "zh": "儒鴻", "en": "Eclat"},
            {"code": "1477", "zh": "聚陽", "en": "Makalot"},
            {"code": "1440", "zh": "南紡", "en": "Tainan Spinning"},
            {"code": "1444", "zh": "力麗", "en": "Lealea"}
        ]
    },
    "1102": {
        "name": "水泥工業 (Cement)", 
        "peers": [
            {"code": "1102", "zh": "亞泥", "en": "ACC"},
            {"code": "1101", "zh": "台泥", "en": "TCC"},
            {"code": "1103", "zh": "嘉泥", "en": "CHC"},
            {"code": "1108", "zh": "幸福", "en": "Hsing Ta"},
            {"code": "1109", "zh": "信大", "en": "Hsin Ta"}
        ]
    },
    "4904": {
        "name": "通信網路 (Telecommunications)", 
        "peers": [
            {"code": "4904", "zh": "遠傳", "en": "FET"},
            {"code": "2412", "zh": "中華電", "en": "CHT"},
            {"code": "3045", "zh": "台灣大", "en": "TWM"}
        ]
    }
}

# === 三歲小孩商業模式辭典 ===
ELI3_MODELS = {
    "1402": "👶 **賣什麼**：我們做衣服的布料，還有裝飲料的寶特瓶唷！<br>💰 **怎麼賺錢**：把石油變成神奇的塑膠粒，再把它們變成好穿的衣服賣給 Nike 這種大公司！<br>⚙️ **商業模式**：從最原始的原料到最後的衣服，全部自己做（垂直整合）。靠著技術厲害、成本便宜，賺取中間的差價。",
    "1102": "👶 **賣什麼**：蓋房子、造橋鋪路用的灰灰粉末，叫做「水泥」！<br>💰 **怎麼賺錢**：把山上的石頭挖下來，放進超熱的大爐子裡烤，變成水泥後賣給蓋房子的工人。<br>⚙️ **商業模式**：水泥很重，運費很貴，所以我們在很多地方都蓋了工廠，誰離我們近就賣給誰，靠控制煤炭成本和投資其他公司來賺錢。",
    "4904": "👶 **賣什麼**：賣讓你的手機可以上網看影片、打電話的「隱形電波」！<br>💰 **怎麼賺錢**：每個月收爸爸媽媽的電話費和網路費。<br>⚙️ **商業模式**：花很多錢蓋高高的基地台（這叫資本資出），然後像收過路費一樣，每個月向大家收月租費，這就是超穩定的現金流！"
}

@st.cache_data(ttl=86400)
def fetch_peer_history_for_baseline(peers):
    """抓取同業近半年歷史價格，用於計算基準相對強度"""
    hist_dict = {}
    for p in peers:
        df = fetch_twse_history_proxy(p['code'])
        if df:
            temp_df = pd.DataFrame(df)[['date', 'close']]
            temp_df.rename(columns={'close': f"{p['zh']}_{p['code']}"}, inplace=True)
            hist_dict[p['code']] = temp_df
    
    if not hist_dict: return pd.DataFrame()
    
    # 合併所有 DataFrame
    main_df = list(hist_dict.values())[0]
    for code, df in list(hist_dict.items())[1:]:
        main_df = pd.merge(main_df, df, on='date', how='inner')
    return main_df

# === 繪圖模組 ===
def plot_relative_strength_base100(df, target_col):
    """繪製以目標股票為 100 基準線的相對強度對比圖"""
    df = df.copy()
    df.set_index(pd.to_datetime(df['date']), inplace=True)
    df.drop(columns=['date'], inplace=True)
    
    # 步驟 1：將所有股票各自對齊第一天的價格，算出成長率
    normalized_df = df.div(df.iloc[0]) 
    
    # 步驟 2：將目標股票的成長率設為分母，算出相對於目標的強弱 (Base 100)
    relative_df = (normalized_df.div(normalized_df[target_col], axis=0)) * 100
    
    fig = go.Figure()
    # 畫基準線 (目標股票永遠是一條 100 的平線)
    fig.add_trace(go.Scatter(x=relative_df.index, y=relative_df[target_col], mode='lines', name=f"基準: {target_col.split('_')[0]} (100)", line=dict(color='#0f172a', width=4)))
    
    # 畫同業比較線
    colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
    color_idx = 0
    for col in relative_df.columns:
        if col != target_col:
            fig.add_trace(go.Scatter(x=relative_df.index, y=relative_df[col], mode='lines', name=col.split('_')[0], line=dict(width=2, color=colors[color_idx % len(colors)])))
            color_idx += 1
            
    fig.update_layout(
        title="<b>🛡️ 戰略雷達：產業相對強弱對比 (Target = 100)</b>", 
        yaxis_title="相對基準表現",
        height=400, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', hovermode="x unified"
    )
    return fig

# === 主控台區塊 ===
market_categories = {
    "🏢 遠東集團核心事業體": {"🇹🇼 1402 遠東新": "1402", "🇹🇼 1102 亞泥": "1102", "🇹🇼 2606 裕民": "2606", "🇹🇼 4904 遠傳": "4904"}
}

with st.sidebar:
    st.header("🎯 戰略監控目標")
    selected_category = st.selectbox("板塊分類", list(market_categories.keys()))
    st.markdown("---")
    options_dict = market_categories[selected_category]
    option = st.radio("監控標的", list(options_dict.keys()))
    code = options_dict[option]

# === 基礎報價獲取 ===
current_price, prev_close = 0, 0
real_data = {'open': '-', 'high': '-', 'low': '-', 'volume': '-'}

try:
    real = twstock.realtime.get(code)
    if real['success']:
        info = real['realtime']
        current_price = float(info['latest_trade_price']) if info['latest_trade_price'] != '-' else float(info['open'])
        prev_close = float(real['info']['y'])
        real_data.update({'open': info.get('open'), 'high': info.get('high'), 'low': info.get('low'), 'volume': info.get('accumulate_trade_volume')})
except: pass

change = current_price - prev_close
pct = ((current_price - prev_close)/prev_close)*100 if prev_close else 0

# === 畫面呈現：Top Cards ===
bg_color, font_color, border_color = "#f8fafc", "#dc2626" if change >= 0 else "#16a34a", "#fca5a5" if change >= 0 else "#86efac"

st.markdown(f"""
<div style="background-color: {bg_color}; padding: 25px; border-radius: 8px; margin-bottom: 25px; border-left: 6px solid {border_color};">
    <h2 style="margin:0; color:#475569; font-size: 1.1rem;">{option}</h2>
    <div style="display: flex; align-items: baseline; gap: 15px; margin-top: 8px;">
        <span style="font-size: 3.2rem; font-weight: 700; color: #0f172a;">NT$ {current_price:,.2f}</span>
        <span style="font-size: 1.5rem; font-weight: 600; color: {font_color};">{change:+.2f} ({pct:+.2f}%)</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# === 📈 企業基本面與產業戰略解析 ===
# ==========================================
st.divider()
st.markdown("### 📈 企業基本面與產業戰略解析")

# 三歲小孩商業模式
if code in ELI3_MODELS:
    st.markdown(f'<div class="eli3-box"><b>🧸 3歲小孩也懂的商業模式：</b><br>{ELI3_MODELS[code]}</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📊 營收與獲利 (Yahoo TW 同步)", "⚔️ 產業相對強弱 (Base 100)"])

with tab1:
    st.markdown("**來自 Yahoo Finance TW 的即時抓取資料：**")
    
    # 呼叫爬蟲
    scraped_data = scrape_yahoo_tw_financials(code)
    
    col_rev, col_eps = st.columns(2)
    with col_rev:
        st.markdown("#### 📅 單月營收追蹤")
        if scraped_data["revenue"]:
            st.dataframe(pd.DataFrame(scraped_data["revenue"]), use_container_width=True, hide_index=True)
        else:
            st.warning("目前無法解析該檔股票之 Yahoo TW 營收表格，請檢查網路狀態或確認頁面結構未變動。")
            
    with col_eps:
        st.markdown("#### 💰 單季 EPS (每股盈餘)")
        if scraped_data["eps"]:
            st.dataframe(pd.DataFrame(scraped_data["eps"]), use_container_width=True, hide_index=True)
        else:
            st.warning("目前無法解析該檔股票之 Yahoo TW EPS 表格。")

with tab2:
    if code in INDUSTRY_PEERS:
        peer_info = INDUSTRY_PEERS[code]
        st.markdown(f"**目標賽道：{peer_info['name']}**")
        
        # 顯示雙語對標清單
        peer_list_display = " | ".join([f"{p['zh']} ({p['en']})" for p in peer_info['peers']])
        st.caption(f"觀測名單：{peer_list_display}")
        
        # 抓取歷史資料並繪製基準 100 圖表
        target_col_name = next((f"{p['zh']}_{p['code']}" for p in peer_info['peers'] if p['code'] == code), None)
        df_peers_hist = fetch_peer_history_for_baseline(peer_info['peers'])
        
        if not df_peers_hist.empty and target_col_name:
            st.plotly_chart(plot_relative_strength_base100(df_peers_hist, target_col_name), use_container_width=True)
            st.info(f"💡 **判讀邏輯**：此圖表將 **{option.split(' ')[-1]}** 的歷史走勢強制拉直為 100。如果對手的線條向上突破 100，代表該期間對手的漲幅跑贏了我們；如果線條低於 100，代表我們的護城河發揮效用，績效擊敗了同行！")
    else:
        st.info("該標的目前未配置同業對標追蹤清單。")
