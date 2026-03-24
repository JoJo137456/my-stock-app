import streamlit as st
import twstock
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, time as dt_time
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

# === 淺藍系現代化登入介面 ===
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
        [data-testid="column"]:nth-of-type(3) { background: #ffffff; border-radius: 20px; padding: 40px 35px; box-shadow: 0 15px 35px rgba(0,0,0,0.04); margin-top: 20px; }
        div[data-baseweb="input"] > div { border: 1px solid #E0E0E0 !important; background-color: #ffffff !important; border-radius: 8px !important; height: 52px !important; }
        button[kind="primary"] { background-color: #1A1B20 !important; color: white !important; border-radius: 8px !important; height: 50px !important; font-weight: 600 !important; }
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

if not check_password(): st.stop()

# ==========================================
# === 2. 核心 UI 樣式設定 ===
# ==========================================
st.markdown("""
    <style>
        html, body, [class*="css"] { font-family: 'Noto Sans TC', 'Microsoft JhengHei', sans-serif !important; }
        .main-title { font-size: 2.2rem; font-weight: 800; color: #1e293b; text-align: center; margin: 1rem 0; letter-spacing: 1px;}
        .sub-title { font-size: 1rem; color: #64748b; text-align: center; margin-bottom: 2rem; font-weight: 500;}
        .ai-score-box { background: linear-gradient(135deg, #1e293b, #0f172a); color: white; padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.15);}
        .fraud-box-safe { background: #ffffff; border-left: 5px solid #22c55e; padding: 15px; border-radius: 8px; margin-top:15px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);}
        .fraud-box-warn { background: #ffffff; border-left: 5px solid #ef4444; padding: 15px; border-radius: 8px; margin-top:15px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);}
        
        .minimal-list { padding-left: 1.2rem; margin-top: 0.5rem; margin-bottom: 0;}
        .minimal-list li { margin-bottom: 0.6rem; }
        [data-testid="stSidebar"] .stRadio label p,
        [data-testid="stSidebar"] .stSelectbox label p { font-size: 1.15rem !important; font-weight: 600 !important; color: #1e293b !important; }
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label div p { font-size: 1.25rem !important; padding: 4px 0px; }
    </style>
""", unsafe_allow_html=True)
st.markdown('<div class="main-title">遠東集團 (Far Eastern Group)</div><div class="sub-title">聯合稽核總部 ｜ 戰略決策儀表板</div>', unsafe_allow_html=True)

# ==========================================
# === 3. 共用工具與外部 API ===
# ==========================================
def safe_extract(row, keys, default=0.0):
    """彈性資料提取器：負責尋找多種可能的欄位名稱，防禦改名風險"""
    for key in keys:
        if key in row and pd.notna(row[key]):
            try:
                val = float(str(row[key]).replace(',', ''))
                return val
            except: pass
    return default

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
        ticker = yf.Ticker(stock_code if is_us_source else f"{stock_code}.TW")
        df = ticker.history(period="1d", interval="1m")
        if df.empty:
            df = ticker.history(period="5d", interval="5m")
            if not df.empty: df = df[df.index.date == df.index[-1].date()]
        return df if not df.empty else None
    except: return None

# ==========================================
# === 4. TEJ 真實數據引擎 (核心替換) ===
# ==========================================
def get_resilient_financials(stock_code):
    if 'df_tej' not in st.session_state or st.session_state['df_tej'].empty:
        return pd.DataFrame(), pd.DataFrame()
        
    df_all = st.session_state['df_tej']
    
    try:
        # 強制轉換代號型態以確保比對成功
        df_target = df_all[df_all['代號'].astype(str).str.strip() == str(stock_code)].copy()
    except KeyError:
        return pd.DataFrame(), pd.DataFrame()

    if df_target.empty:
        return pd.DataFrame(), pd.DataFrame()

    df_target = df_target.sort_values(by='年/月', ascending=False).head(8)
    
    results = []
    for _, row in df_target.iterrows():
        # TEJ 預設單位多為「千元」，除以 100,000 轉為「億」
        rev = safe_extract(row, ['營業收入淨額', '營業收入', '營收淨額']) / 100000
        gp = safe_extract(row, ['營業毛利（毛損）', '營業毛利', '營業毛利(損)']) / 100000
        net = safe_extract(row, ['本期淨利（淨損）', '本期淨利', '稅後淨利']) / 100000
        opex = safe_extract(row, ['營業費用', '推銷費用', '管理費用']) / 100000 # 概算
        eps = safe_extract(row, ['基本每股盈餘（元）', '每股盈餘', 'EPS'])
        
        # 週轉天數
        inv_days = safe_extract(row, ['存貨週轉天數（次）', '存貨週轉天數', '存貨天數'])
        ar_days = safe_extract(row, ['應收帳款週轉天數（次）', '應收帳款週轉天數', '應收帳款天數'])
        
        gp_margin = (gp / rev * 100) if rev != 0 else 0
        net_margin = (net / rev * 100) if rev != 0 else 0
        
        results.append({
            '季度': str(row.get('年/月', '未知')), 
            '單季營收 (億)': round(rev, 1), 
            '毛利 (億)': round(gp, 1), 
            '毛利率 (%)': round(gp_margin, 1),
            '營業費用 (億)': round(opex, 1), 
            '淨利 (億)': round(net, 1), 
            '淨利率 (%)': round(net_margin, 1),
            '單季EPS (元)': round(eps, 2), 
            '存貨周轉天數': round(inv_days, 1), 
            '應收帳款天數': round(ar_days, 1)
        })
            
    df = pd.DataFrame(results)
    
    if not df.empty:
        ytd_df = df.copy().iloc[::-1].reset_index(drop=True)
        ytd_df['年份'] = ytd_df['季度'].str[:4]
        ytd_df['累計營收 (億)'] = ytd_df.groupby('年份')['單季營收 (億)'].cumsum()
        ytd_df['累計毛利 (億)'] = ytd_df.groupby('年份')['毛利 (億)'].cumsum()
        ytd_df['累計淨利 (億)'] = ytd_df.groupby('年份')['淨利 (億)'].cumsum()
        ytd_df['累計EPS (元)'] = ytd_df.groupby('年份')['單季EPS (元)'].cumsum()
        ytd_df = ytd_df.iloc[::-1].drop(columns=['年份']).reset_index(drop=True)
        return df, ytd_df
    return pd.DataFrame(), pd.DataFrame()

def calculate_ai_audit_score(df):
    if len(df) < 2: return 50, "數據不足", "安全"
    latest = df.iloc[0]
    prev = df.iloc[1]
    score = 80 
    trend_notes = []
    
    if latest['單季營收 (億)'] > prev['單季營收 (億)']: trend_notes.append("✅ 營收動能向上")
    else: score -= 5; trend_notes.append("⚠️ 營收動能衰退")
        
    if latest['毛利率 (%)'] >= prev['毛利率 (%)']: trend_notes.append("✅ 毛利率穩健")
    else: score -= 5; trend_notes.append("⚠️ 毛利率壓縮")

    fraud_risk_msgs = []
    
    dsri = latest['應收帳款天數'] / prev['應收帳款天數'] if prev['應收帳款天數'] > 0 else 1
    if dsri > 1.25:
        score -= 15
        fraud_risk_msgs.append(f"🟥 高風險：應收帳款天數暴增 (DSRI={dsri:.2f})，具備塞貨或客戶違約風險。")
    
    inv_index = latest['存貨周轉天數'] / prev['存貨周轉天數'] if prev['存貨周轉天數'] > 0 else 1
    if inv_index > 1.2:
        score -= 10
        fraud_risk_msgs.append(f"🟧 中風險：庫存去化嚴重放緩，資金積壓增加。")
        
    gmi = prev['毛利率 (%)'] / latest['毛利率 (%)'] if latest['毛利率 (%)'] > 0 else 1
    if gmi > 1.15:
        score -= 10
        fraud_risk_msgs.append(f"🟧 中風險：毛利率顯著惡化 (GMI={gmi:.2f})，定價能力喪失。")

    if not fraud_risk_msgs:
        fraud_risk = "🟩 正常 (未見異常財務特徵，資產品質與營運現金流健康)"
    else:
        fraud_risk = "<br>".join(fraud_risk_msgs)

    score = max(0, min(100, int(score)))
    return score, " | ".join(trend_notes), fraud_risk

# ==========================================
# === 5. 戰略資料庫與繪圖 ===
# ==========================================
MACRO_IMPACT = {
    "🇹🇼 台灣加權指數": "台灣加權指數為台灣整體經濟及半導體產業景氣的綜合指標。主要與台積電等科技巨頭連動，可作為評估外資資金流向及國內資本市場活力的關鍵參考。",
    "🇺🇸 S&P 500": "S&P 500 指數涵蓋美國前 500 大企業，代表美國實體經濟的全貌。其涵蓋多樣產業，為全球長期資金配置及美股市場多空趨勢判斷的基準指標。",
    "🇺🇸 Dow Jones": "道瓊工業指數涵蓋 30 家歷史悠久的美國藍籌企業（涵蓋工業、金融等領域）。有助於評估美國傳統經濟基礎的穩健性，並對傳統企業獲利能力高度敏感。",
    "🇺🇸 Nasdaq": "納斯達克指數為全球科技創新的領先指標，聚集微軟、蘋果等科技巨頭。直接反映市場對 AI、軟硬體等高科技領域資本支出的成長預期。",
    "🇺🇸 SOX (費半)": "費城半導體指數為全球半導體產業鏈的核心指標，涵蓋晶片設計至設備製造等環節，可精準預測電子業庫存循環及終端需求趨勢。",
    "⚠️ VIX 恐慌指數": "VIX 恐慌指數用以衡量市場投資人的恐慌程度。當指數大幅上升時，顯示投資人預期未來市場波動加劇，常伴隨股市下跌，為重要的避險指標。"
}

INDUSTRY_PEERS = {
    "1402": {"name": "紡織纖維", "peers": [{"code": "1402", "name": "遠東新"}, {"code": "1476", "name": "儒鴻"}, {"code": "1477", "name": "聚陽"}, {"code": "1440", "name": "南紡"}, {"code": "1444", "name": "力麗"}]},
    "1102": {"name": "水泥工業", "peers": [{"code": "1102", "name": "亞泥"}, {"code": "1101", "name": "台泥"}, {"code": "1103", "name": "嘉泥"}, {"code": "1108", "name": "幸福"}, {"code": "1109", "name": "信大"}]},
    "2606": {"name": "航運業", "peers": [{"code": "2606", "name": "裕民"}, {"code": "2637", "name": "慧洋-KY"}, {"code": "2605", "name": "新興"}, {"code": "2612", "name": "中航"}, {"code": "2617", "name": "台航"}]},
    "4904": {"name": "通信網路", "peers": [{"code": "4904", "name": "遠傳"}, {"code": "2412", "name": "中華電"}, {"code": "3045", "name": "台灣大"}]},
    "2903": {"name": "貿易百貨", "peers": [{"code": "2903", "name": "遠百"}, {"code": "2912", "name": "統一超"}, {"code": "8454", "name": "富邦媒"}, {"code": "5904", "name": "寶雅"}, {"code": "2915", "name": "潤泰全"}]},
    "1460": {"name": "紡織纖維", "peers": [{"code": "1460", "name": "宏遠"}, {"code": "1476", "name": "儒鴻"}, {"code": "1477", "name": "聚陽"}, {"code": "1402", "name": "遠東新"}, {"code": "1444", "name": "力麗"}]},
    "1710": {"name": "化學工業", "peers": [{"code": "1710", "name": "東聯"}, {"code": "1301", "name": "台塑"}, {"code": "1303", "name": "南亞"}, {"code": "1326", "name": "台化"}, {"code": "1722", "name": "台肥"}]},
    "2845": {"name": "金融保險", "peers": [{"code": "2845", "name": "遠東銀"}, {"code": "2881", "name": "富邦金"}, {"code": "2882", "name": "國泰金"}, {"code": "2886", "name": "兆豐金"}, {"code": "2891", "name": "中信金"}]}
}

@st.cache_data(ttl=86400)
def fetch_peers_ccc_real(peer_info):
    results = []
    period_label = "最新單季財報 (TEJ 內部資料庫)"
    
    if 'df_tej' not in st.session_state or st.session_state['df_tej'].empty:
        return pd.DataFrame(), "等待資料匯入"
        
    df_all = st.session_state['df_tej']
    
    for p in peer_info['peers']:
        stock_id = p['code']
        df_peer = df_all[df_all['代號'].astype(str).str.strip() == str(stock_id)]
        
        if not df_peer.empty:
            latest_row = df_peer.sort_values(by='年/月', ascending=False).iloc[0]
            
            rev = safe_extract(latest_row, ['營業收入淨額', '營業收入', '營收淨額'])
            gp = safe_extract(latest_row, ['營業毛利（毛損）', '營業毛利', '營業毛利(損)'])
            net = safe_extract(latest_row, ['本期淨利（淨損）', '本期淨利', '稅後淨利'])
            
            gm = (gp / rev * 100) if rev > 0 else 0
            nm = (net / rev * 100) if rev > 0 else 0
            
            inv_days = safe_extract(latest_row, ['存貨週轉天數（次）', '存貨週轉天數', '存貨天數'])
            ar_days = safe_extract(latest_row, ['應收帳款週轉天數（次）', '應收帳款週轉天數', '應收帳款天數'])
            roe = safe_extract(latest_row, ['ROE(A)－稅後', 'ROE', '股東權益報酬率'])
            
            results.append({
                "公司": f"{p['name']} ({stock_id})",
                "毛利率 (%)": round(gm, 1),
                "淨利率 (%)": round(nm, 1),
                "ROE (%)": round(roe, 1),
                "存貨周轉天數": round(inv_days, 1),
                "應收帳款天數": round(ar_days, 1)
            })
                
    return pd.DataFrame(results), period_label

def plot_daily_k(df):
    if df.empty: return None
    df = df.copy()
    df.set_index(pd.to_datetime(df['date']), inplace=True)
    df = df.tail(120)
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], increasing_line_color='#ef4444', increasing_fillcolor='#ef4444', decreasing_line_color='#22c55e', decreasing_fillcolor='#22c55e', name="日K")])
    fig.update_layout(title="<b>📊 歷史價格走勢 (近半年)</b>", xaxis_rangeslider_visible=False, height=380, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor='#ffffff', plot_bgcolor='#ffffff')
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#f1f5f9')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f1f5f9')
    return fig

def plot_intraday_line(df):
    if df is None or df.empty: return None
    y_min, y_max = df['Close'].min(), df['Close'].max()
    padding = (y_max - y_min) * 0.1 if y_max != y_min else y_max * 0.01
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', line=dict(color='#0f172a', width=2.5), fill='tozeroy', fillcolor='rgba(15, 23, 42, 0.05)', name='報價'))
    fig.update_layout(title="<b>⚡ 當日分時動態</b>", height=380, margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified", paper_bgcolor='#ffffff', plot_bgcolor='#ffffff', yaxis=dict(range=[y_min - padding, y_max + padding]))
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#f1f5f9')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f1f5f9')
    return fig

# ==========================================
# === 6. UI 互動與架構 ===
# ==========================================
market_categories = {
    "📈 總體經濟與大盤 (宏觀指標)": {
        "🇹🇼 台灣加權指數": "^TWII", "🇺🇸 S&P 500": "^GSPC", "🇺🇸 Dow Jones": "^DJI", "🇺🇸 Nasdaq": "^IXIC",
        "🇺🇸 SOX (費半)": "^SOX", "⚠️ VIX 恐慌指數": "^VIX"
    },
    "🏢 遠東集團核心事業體": {
        "👕 1402 遠東新": "1402", "🏗️ 1102 亞泥": "1102", "🚢 2606 裕民": "2606", "🧵 1460 宏遠": "1460",
        "🛍️ 2903 遠百": "2903", "📱 4904 遠傳": "4904", "🧪 1710 東聯": "1710", "🏦 2845 遠東銀": "2845"
    }
}

with st.sidebar:
    st.header("📂 TEJ 內部資料匯入")
    uploaded_files = st.file_uploader("請上傳 TEJ 財務資料 (.xlsx)", type=["xlsx", "xls"], accept_multiple_files=True)
    
    if uploaded_files:
        try:
            df_list = []
            for file in uploaded_files:
                df = pd.read_excel(file)
                df_list.append(df)
            df_tej_combined = pd.concat(df_list, ignore_index=True)
            st.session_state['df_tej'] = df_tej_combined
            st.success(f"✅ 成功合併 {len(uploaded_files)} 個檔案！共 {len(df_tej_combined)} 筆資料")
            with st.expander("👀 預覽合併後的 TEJ 資料"):
                st.dataframe(df_tej_combined.head(5))
        except Exception as e:
            st.error(f"❌ 讀取失敗。錯誤：{e}")

    st.markdown("---")
    st.header("🎯 戰略監控目標")
    selected_category = st.selectbox("板塊分類", list(market_categories.keys()))
    st.markdown("---")
    options_dict = market_categories[selected_category]
    option = st.radio("監控標的", list(options_dict.keys()))
    code = options_dict[option]
    
    is_tw_stock = code.isdigit()

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

current_price = real_data['price']
if (current_price == 0 or current_price is None) and not df_daily.empty:
    current_price = df_daily.iloc[-1]['close']

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

col1, col2 = st.columns([1, 1])
with col1:
    if df_intra is not None and not df_intra.empty: st.plotly_chart(plot_intraday_line(df_intra), use_container_width=True)
with col2:
    if not df_daily.empty: st.plotly_chart(plot_daily_k(df_daily), use_container_width=True)

# ==========================================
# === 7. 高階戰情室 (資料綁定) ===
# ==========================================
if is_tw_stock:
    st.divider()
    st.markdown("## 📈 企業基本面與高階戰略解析 (Executive Financials)")
    
    # 從 TEJ 抓取資料
    df_quarterly, df_ytd = get_resilient_financials(code)
    
    if df_quarterly.empty:
        st.info("💡 請從左側選單上傳包含該公司代號的 TEJ 財務資料 Excel 檔，以解鎖高階財務分析功能。")
    elif len(df_quarterly) >= 2:
        latest = df_quarterly.iloc[0]
        st.markdown("### 🤖 稽核 AI 財報健檢與風險偵測 (Audit AI Engine)")
        ai_score, ai_trend, fraud_risk = calculate_ai_audit_score(df_quarterly)
        
        col_ai1, col_ai2 = st.columns([1, 2.5])
        with col_ai1:
            st.markdown(f"""<div class="ai-score-box"><div style="font-size:14px; color:#94a3b8;">AI 綜合查核評分</div><div style="font-size:48px; font-weight:800; color:{'#4ade80' if ai_score>=70 else '#f87171'};">{ai_score}</div><div style="font-size:13px;">{ai_trend}</div></div>""", unsafe_allow_html=True)
        with col_ai2:
            box_class = "fraud-box-warn" if "風險" in fraud_risk else "fraud-box-safe"
            st.markdown(f"""<div class="{box_class}"><div style="font-weight:700; margin-bottom:5px; font-size:16px;">⚖️ 財報舞弊與資產品質風險 (Fraud & Asset Quality Risk)</div><div style="font-size:15px;">{fraud_risk}</div><div style="font-size:12px; color:#64748b; margin-top:8px;">*指標說明：以 DSRI 與 GMI 模型交叉比對應收帳款與存貨周轉效率之異常波動。</div></div>""", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        c_chart1, c_chart2 = st.columns([1, 1.2])
        with c_chart1:
            plot_df = df_quarterly.iloc[::-1]
            fig1 = make_subplots(specs=[[{"secondary_y": True}]])
            fig1.add_trace(go.Bar(x=plot_df['季度'], y=plot_df['單季營收 (億)'], name="營收 (億)", marker_color='#CBD5E1'), secondary_y=False)
            fig1.add_trace(go.Scatter(x=plot_df['季度'], y=plot_df['毛利率 (%)'], name="毛利率 %", mode='lines+markers', line=dict(color='#0F172A', width=3)), secondary_y=True)
            fig1.add_trace(go.Scatter(x=plot_df['季度'], y=plot_df['淨利率 (%)'], name="淨利率 %", mode='lines+markers', line=dict(color='#3B82F6', width=2)), secondary_y=True)
            fig1.update_layout(title="<b>📊 營收規模與獲利能力趨勢 (近8季)</b>", height=380, margin=dict(l=0, r=0, t=40, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), paper_bgcolor='#ffffff', plot_bgcolor='#ffffff')
            st.plotly_chart(fig1, use_container_width=True)
            
        with c_chart2:
            fig2 = go.Figure(go.Waterfall(
                name="20", orientation="v", measure=["relative", "relative", "total", "relative", "total"],
                x=["營業收入", "營業成本", "毛利", "營業費用/稅等", "本期淨利"], textposition="outside", textfont=dict(size=14),
                text=[f"{latest['單季營收 (億)']}", f"-{latest['單季營收 (億)'] - latest['毛利 (億)']:.1f}", f"{latest['毛利 (億)']}", f"-{latest['毛利 (億)'] - latest['淨利 (億)']:.1f}", f"{latest['淨利 (億)']}"],
                y=[latest['單季營收 (億)'], -(latest['單季營收 (億)'] - latest['毛利 (億)']), latest['毛利 (億)'], -(latest['毛利 (億)'] - latest['淨利 (億)']), latest['淨利 (億)']],
                connector={"line":{"color":"#CBD5E1", "dash": 'dot', "width": 2}}, decreasing={"marker":{"color":"#22c55e"}}, increasing={"marker":{"color":"#ef4444"}}, totals={"marker":{"color":"#1F2937"}}
            ))
            fig2.update_layout(title=f"<b>💰 獲利結構拆解 (最新季度: {latest['季度']})</b>", height=380, margin=dict(l=0, r=0, t=50, b=0), paper_bgcolor='#ffffff', plot_bgcolor='#ffffff')
            st.plotly_chart(fig2, use_container_width=True)
            
        if code in INDUSTRY_PEERS:
            st.markdown("### ⚔️ 產業營運週期對標矩陣 (Cash Conversion Cycle Matrix)")
            peer_info = INDUSTRY_PEERS[code]
            st.caption(f"📍 目標賽道：{peer_info['name']} | 分析指標：存貨周轉 vs 應收帳款天數")
            df_peers_ccc, period_label = fetch_peers_ccc_real(peer_info)
            
            if not df_peers_ccc.empty:
                if code == "2845": # 金融保險業不看存貨
                    ccc_fig = go.Figure()
                    ccc_fig.add_trace(go.Bar(x=df_peers_ccc['公司'], y=df_peers_ccc['ROE (%)'], name='ROE (%)', marker_color='#0F172A'))
                    ccc_fig.update_layout(title="<b>🏦 金融業獲利指標 (ROE)</b>", height=400, paper_bgcolor='#ffffff', plot_bgcolor='#ffffff')
                else:
                    ccc_fig = go.Figure()
                    ccc_fig.add_trace(go.Scatter(
                        x=df_peers_ccc['應收帳款天數'], y=df_peers_ccc['存貨周轉天數'],
                        mode='markers+text', text=df_peers_ccc['公司'].str.split(' ').str[0], textposition="top center",
                        marker=dict(size=25, color=df_peers_ccc['毛利率 (%)'], colorscale='Viridis', showscale=True, colorbar=dict(title="毛利率%")),
                        hovertemplate="<b>%{text}</b><br>應收帳款天數: %{x}<br>存貨周轉天數: %{y}<br>毛利率: %{marker.color}%<extra></extra>"
                    ))
                    
                    ccc_fig.update_layout(
                        title=f"<b>🎯 營運效率與變現能力矩陣 (資料基準: {period_label})</b>",
                        xaxis=dict(autorange="reversed", title="應收帳款周轉天數 (天) 👉 右方代表收款極快", showgrid=False),
                        yaxis=dict(autorange="reversed", title="存貨周轉天數 (天) 👆 上方代表產品熱銷無積壓", showgrid=True, gridcolor='#F1F5F9'),
                        height=450, margin=dict(l=20, r=20, t=60, b=20), paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
                        annotations=[
                            dict(x=0.95, y=0.95, xref="paper", yref="paper", text="<b>🥇 變現王者</b><br>貨賣得快/錢收得快", showarrow=False, font=dict(color="#10B981")),
                            dict(x=0.05, y=0.05, xref="paper", yref="paper", text="<b>⚠️ 資金卡死區</b><br>庫存高/被客戶欠款", showarrow=False, font=dict(color="#EF4444"))
                        ]
                    )
                    ccc_fig.add_hline(y=df_peers_ccc['存貨周轉天數'].median(), line_dash="dot", line_color="#94A3B8")
                    ccc_fig.add_vline(x=df_peers_ccc['應收帳款天數'].median(), line_dash="dot", line_color="#94A3B8")
                    
                st.plotly_chart(ccc_fig, use_container_width=True)
                
        st.markdown("### 📑 核心財務數據矩陣")
        tab1, tab2 = st.tabs(["📊 單季表現 (Quarterly)", "📈 累計表現 (Year-To-Date)"])
        format_dict = {'單季營收 (億)': '{:,.1f}', '毛利 (億)': '{:,.1f}', '營業費用 (億)': '{:,.1f}', '淨利 (億)': '{:,.1f}', '毛利率 (%)': '{:.1f}%', '淨利率 (%)': '{:.1f}%', '單季EPS (元)': '{:.2f}', '存貨周轉天數': '{:.1f}', '應收帳款天數': '{:.1f}'}
        with tab1: st.dataframe(df_quarterly.style.format(format_dict), use_container_width=True, height=320)
        with tab2:
            if not df_ytd.empty:
                ytd_cols = ['季度', '累計營收 (億)', '累計毛利 (億)', '毛利率 (%)', '累計淨利 (億)', '淨利率 (%)', '累計EPS (元)']
                format_ytd = {'累計營收 (億)': '{:,.1f}', '累計毛利 (億)': '{:,.1f}', '累計淨利 (億)': '{:,.1f}', '毛利率 (%)': '{:.1f}%', '淨利率 (%)': '{:.1f}%', '累計EPS (元)': '{:.2f}'}
                st.dataframe(df_ytd[ytd_cols].style.format(format_ytd), use_container_width=True, height=320)
    else:
        st.warning("⚠️ 查無足夠的歷史季報，或資料欄位未能成功對應。請確認上傳的 Excel 是否包含該公司資料。")

update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f'<div style="text-align:center; color:#94a3b8; font-size:0.8rem; margin-top:3rem;">系統更新時間：{update_time} ｜ 資料庫：TEJ (內部匯入)</div>', unsafe_allow_html=True)
