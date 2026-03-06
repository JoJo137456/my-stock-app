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
import numpy as np

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
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">遠東集團 (Far Eastern Group)</div><div class="sub-title">聯合稽核總部 ｜ 戰略決策儀表板</div>', unsafe_allow_html=True)

# === API 與資料抓取模組 (整合既有與新增) ===
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

@st.cache_data(ttl=86400)
def fetch_fundamental_data(stock_code, is_tw_stock):
    """抓取財務基本面資料"""
    try:
        ticker = yf.Ticker(f"{stock_code}.TW" if is_tw_stock else stock_code)
        info = ticker.info
        
        # 取得最新年度與季度財報
        inc_stmt_ann = ticker.income_stmt
        inc_stmt_qtr = ticker.quarterly_income_stmt
        cf_ann = ticker.cashflow
        cf_qtr = ticker.quarterly_cashflow
        
        return {
            "info": info,
            "annual_inc": inc_stmt_ann,
            "quarterly_inc": inc_stmt_qtr,
            "annual_cf": cf_ann,
            "quarterly_cf": cf_qtr
        }
    except:
        return None

# === 同業競爭對標清單 (自動分類) ===
INDUSTRY_PEERS = {
    "1402": {"name": "紡織纖維", "peers": ["1402", "1476", "1477", "1440", "1444"]},
    "1102": {"name": "水泥工業", "peers": ["1101", "1102", "1103", "1108", "1109"]},
    "2606": {"name": "航運業", "peers": ["2606", "2603", "2609", "2615", "2637"]},
    "4904": {"name": "通信網路", "peers": ["2412", "3045", "4904"]},
    "2903": {"name": "貿易百貨", "peers": ["2903", "2912", "2915", "5904"]},
    "1710": {"name": "化學工業", "peers": ["1710", "1301", "1303", "1326", "1722"]},
    "2845": {"name": "金融保險", "peers": ["2845", "2881", "2882", "2886", "2891"]},
}

@st.cache_data(ttl=86400)
def fetch_peers_data(peer_codes):
    """抓取同業基礎估值指標"""
    results = []
    for p in peer_codes:
        try:
            tk = yf.Ticker(f"{p}.TW")
            info = tk.info
            results.append({
                "Code": p,
                "Name": tk.info.get('shortName', p),
                "EPS (TTM)": info.get('trailingEps', 0),
                "毛利率 (%)": info.get('grossMargins', 0) * 100 if info.get('grossMargins') else 0,
                "淨利率 (%)": info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0,
                "ROE (%)": info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0
            })
        except: continue
    return pd.DataFrame(results)

# === 繪圖模組 (沿用舊版 + 新增) ===
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
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', line=dict(color='#0f172a', width=2.5), fill='tozeroy', fillcolor='rgba(15, 23, 42, 0.05)'))
    fig.update_layout(title="<b>⚡ 當日分時動態</b>", height=350, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', hovermode="x unified")
    return fig

def plot_peer_comparison_chart(df_peers):
    if df_peers.empty: return None
    fig = px.bar(df_peers, x='Code', y=['毛利率 (%)', '淨利率 (%)'], barmode='group', title="<b>🛡️ 產業獲利能力對標 (Margins Comparison)</b>", color_discrete_sequence=['#3b82f6', '#10b981'])
    fig.update_layout(height=350, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig

# === 主控台區塊 ===
market_categories = {
    "🏢 遠東集團核心事業體": {"🇹🇼 1402 遠東新": "1402", "🇹🇼 1102 亞泥": "1102", "🇹🇼 2606 裕民": "2606", "🇹🇼 1460 宏遠": "1460", "🇹🇼 2903 遠百": "2903", "🇹🇼 4904 遠傳": "4904", "🇹🇼 1710 東聯": "1710", "🇹🇼 2845 遠東銀": "2845"},
    "📈 總體經濟與大盤": {"🇹🇼 台灣加權指數": "^TWII", "🇺🇸 S&P 500": "^GSPC", "🇺🇸 SOX (費半)": "^SOX", "⚠️ VIX": "^VIX", "🏦 U.S. 10Y": "^TNX", "💵 美元指數": "DX-Y.NYB"}
}

with st.sidebar:
    st.header("🎯 戰略監控目標")
    selected_category = st.selectbox("板塊分類", list(market_categories.keys()))
    st.markdown("---")
    options_dict = market_categories[selected_category]
    option = st.radio("監控標的", list(options_dict.keys()))
    code = options_dict[option]
    
    is_tw_stock = code.isdigit()
    is_index = not is_tw_stock

    if st.button("🔄 刷新全部數據"):
        st.cache_data.clear()
        st.rerun()

# === 基礎報價獲取 ===
current_price, change, pct = 0, 0, 0
real_data = {'open': '-', 'high': '-', 'low': '-', 'volume': '-'}

if is_tw_stock:
    try:
        real = twstock.realtime.get(code)
        if real['success']:
            info = real['realtime']
            current_price = float(info['latest_trade_price']) if info['latest_trade_price'] != '-' else float(info['open'])
            prev_close = float(real['info']['y'])
            change, pct = current_price - prev_close, ((current_price - prev_close)/prev_close)*100
            real_data.update({'open': info.get('open'), 'high': info.get('high'), 'low': info.get('low'), 'volume': info.get('accumulate_trade_volume')})
    except: pass
else:
    try:
        tk = yf.Ticker(code)
        fi = tk.fast_info
        current_price, prev_close = fi.last_price, fi.previous_close
        change, pct = current_price - prev_close, ((current_price - prev_close)/prev_close)*100
        real_data.update({'open': fi.open, 'high': fi.day_high, 'low': fi.day_low, 'volume': f"{int(fi.last_volume):,}"})
    except: pass

# === 畫面呈現：Top Cards ===
bg_color, font_color, border_color = "#f8fafc", "#dc2626" if change >= 0 else "#16a34a", "#fca5a5" if change >= 0 else "#86efac"
currency = "NT$" if is_tw_stock else ("" if is_index else "$")

st.markdown(f"""
<div style="background-color: {bg_color}; padding: 25px; border-radius: 8px; margin-bottom: 25px; border-left: 6px solid {border_color};">
    <h2 style="margin:0; color:#475569; font-size: 1.1rem;">{option}</h2>
    <div style="display: flex; align-items: baseline; gap: 15px; margin-top: 8px;">
        <span style="font-size: 3.2rem; font-weight: 700; color: #0f172a;">{currency} {current_price:,.2f}</span>
        <span style="font-size: 1.5rem; font-weight: 600; color: {font_color};">{change:+.2f} ({pct:+.2f}%)</span>
    </div>
</div>
""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("開盤價", real_data['open'])
c2.metric("最高價", real_data['high'])
c3.metric("最低價", real_data['low'])
c4.metric("成交量", real_data['volume'])

st.divider()

# === 畫面呈現：K線圖 ===
col1, col2 = st.columns(2)
with col1:
    df_intra = get_intraday_chart_data(code, not is_tw_stock)
    if df_intra is not None: st.plotly_chart(plot_intraday_line(df_intra), use_container_width=True)
with col2:
    hist_data = fetch_twse_history_proxy(code) if is_tw_stock else yf.Ticker(code).history(period="6mo").reset_index()
    if is_tw_stock and hist_data:
        st.plotly_chart(plot_daily_k(pd.DataFrame(hist_data)), use_container_width=True)

# ==========================================
# === 新增功能：基本面與產業對標分析 ===
# ==========================================
if is_tw_stock:
    st.markdown("### 📈 企業基本面與產業戰略解析")
    
    # 獲取財報資料
    fin_data = fetch_fundamental_data(code, is_tw_stock)
    info = fin_data['info'] if fin_data else {}
    
    tab1, tab2 = st.tabs(["📊 財務體質檢視 (Financials)", "⚔️ 產業同行對標 (Peers Comparison)"])
    
    with tab1:
        st.markdown("**時間維度選擇 (Timeframe Filter):**")
        time_mode = st.radio("檢視區間", ["年度 (Annual)", "單季 (Quarterly)", "累計 (TTM/YTD)", "單月 (Monthly)"], horizontal=True, label_visibility="collapsed")
        
        # 實作財務數據提取邏輯
        try:
            if "年度" in time_mode and fin_data['annual_inc'] is not None:
                latest_inc = fin_data['annual_inc'].iloc[:, 0] # 最新一年
                latest_cf = fin_data['annual_cf'].iloc[:, 0] if not fin_data['annual_cf'].empty else None
                period_label = latest_inc.name.strftime('%Y') + " 財報"
            else:
                # 預設抓取 Quarterly / TTM 
                latest_inc = fin_data['quarterly_inc'].iloc[:, 0]
                latest_cf = fin_data['quarterly_cf'].iloc[:, 0] if not fin_data['quarterly_cf'].empty else None
                period_label = latest_inc.name.strftime('%Y-Q%m') + " 季報"
                
            rev = latest_inc.get("Total Revenue", 0)
            gp = latest_inc.get("Gross Profit", 0)
            op_exp = latest_inc.get("Operating Expense", 0)
            net_inc = latest_inc.get("Net Income", 0)
            cfo = latest_cf.get("Operating Cash Flow", 0) if latest_cf is not None else 0
            
            # 若選單月，提示需串接 MOPS
            if "單月" in time_mode or "累計" in time_mode:
                st.warning("⚠️ 系統提示：台股單月營收/累計營收需串接「公開資訊觀測站(MOPS)」API。以下顯示由 Yahoo 預估之近四季(TTM)動態指標作為決策參考。")
                rev = info.get('totalRevenue', rev)
                gp = info.get('grossProfits', gp)
                net_inc = info.get('netIncomeToCommon', net_inc)
                cfo = info.get('operatingCashflow', cfo)
                period_label = "TTM (近十二個月)"
        except:
            rev, gp, op_exp, net_inc, cfo = 0, 0, 0, 0, 0
            period_label = "數據讀取中"

        # 格式化單位 (億)
        def fmt_b(val): return f"NT$ {val/100000000:,.1f} 億" if val and pd.notna(val) else "N/A"
        
        st.markdown(f"#### 📅 數據基準：{period_label}")
        f1, f2, f3 = st.columns(3)
        with f1:
            st.markdown(f'<div class="fin-card"><h4>每股盈餘 (EPS)</h4><h2>{info.get("trailingEps", "N/A")}</h2></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="fin-card" style="margin-top:10px;"><h4>營業費用 (Op. Expenses)</h4><h2>{fmt_b(op_exp)}</h2></div>', unsafe_allow_html=True)
        with f2:
            st.markdown(f'<div class="fin-card"><h4>營業收入 (Revenue)</h4><h2>{fmt_b(rev)}</h2></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="fin-card" style="margin-top:10px;"><h4>營業現金流 (Op. Cash Flow)</h4><h2>{fmt_b(cfo)}</h2></div>', unsafe_allow_html=True)
        with f3:
            st.markdown(f'<div class="fin-card"><h4>毛利 (Gross Profit)</h4><h2>{fmt_b(gp)}</h2></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="fin-card" style="margin-top:10px;"><h4>淨利 (Net Income)</h4><h2>{fmt_b(net_inc)}</h2></div>', unsafe_allow_html=True)

    with tab2:
        if code in INDUSTRY_PEERS:
            peer_info = INDUSTRY_PEERS[code]
            st.markdown(f"**目標賽道：{peer_info['name']} (對標前五大龍頭)**")
            
            df_peers = fetch_peers_data(peer_info['peers'])
            if not df_peers.empty:
                st.dataframe(df_peers.style.format({"EPS (TTM)": "{:.2f}", "毛利率 (%)": "{:.1f}%", "淨利率 (%)": "{:.1f}%", "ROE (%)": "{:.1f}%"}), use_container_width=True)
                st.plotly_chart(plot_peer_comparison_chart(df_peers), use_container_width=True)
        else:
            st.info("該標的目前未配置同業對標追蹤清單。")
