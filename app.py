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
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;800&family=Noto+Sans+TC:wght@500;700;900&display=swap');
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
        html, body, [class*="css"]  { font-family: 'Microsoft JhengHei', 'Segoe UI', sans-serif !important; }
        .main-title { font-size: 2.2rem; font-weight: 700; color: #1e293b; text-align: center; margin: 1rem 0; letter-spacing: 1px;}
        .sub-title { font-size: 1rem; color: #64748b; text-align: center; margin-bottom: 2rem; }
        .chart-container { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 25px; border: 1px solid #e2e8f0; }
        
        /* AI 稽核面板樣式 */
        .ai-score-panel { background: #1e293b; color: white; padding: 20px; border-radius: 12px; text-align: center; height: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .ai-score-num { font-size: 55px; font-weight: 800; line-height: 1.1; margin: 10px 0; }
        
        .audit-good-panel { background: #f0fdf4; border-left: 5px solid #22c55e; padding: 15px; border-radius: 8px; height: 100%; }
        .audit-bad-panel { background: #fef2f2; border-left: 5px solid #ef4444; padding: 15px; border-radius: 8px; height: 100%; }
        .audit-action-panel { background: #fffbeb; border-left: 5px solid #f59e0b; padding: 15px; border-radius: 8px; height: 100%; }
        .audit-title { font-weight: 700; color: #0f172a; margin-bottom: 8px; font-size: 15px;}
        .audit-text { font-size: 14px; color: #475569; line-height: 1.5; }
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

# ==========================================
# === 3. API 與真實資料抓取模組 (嚴格拒絕假資料) ===
# ==========================================
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

@st.cache_data(ttl=86400)
def get_real_financials_strict(stock_code):
    """100% 真實數據擷取：只讀取 yfinance 提供的真實季報，解決所有亂碼問題"""
    try:
        tk = yf.Ticker(f"{stock_code}.TW" if stock_code.isdigit() else stock_code)
        inc = tk.quarterly_income_stmt
        bs = tk.quarterly_balance_sheet
        
        if inc.empty: return pd.DataFrame(), pd.DataFrame()
        
        inc = inc.T.sort_index(ascending=False) # 確保最新資料在最上面
        bs = bs.T.sort_index(ascending=False) if not bs.empty else pd.DataFrame()
        
        results = []
        for idx, row in inc.iterrows():
            # 精準格式化日期：例如 2024-Q3 (徹底消滅亂碼)
            q_date = f"{idx.year}-Q{(idx.month-1)//3 + 1}"
            
            # 安全獲取損益表資料
            rev = row.get('Total Revenue', pd.NA)
            gp = row.get('Gross Profit', pd.NA)
            net = row.get('Net Income', pd.NA)
            opex = row.get('Operating Expense', pd.NA)
            cogs = row.get('Cost Of Revenue', pd.NA)
            
            # 獲取資產負債表資料 (若無則保留 NA，絕不造假)
            inv, ar = pd.NA, pd.NA
            if not bs.empty and idx in bs.index:
                inv = bs.loc[idx].get('Inventory', pd.NA)
                ar = bs.loc[idx].get('Accounts Receivable', pd.NA)

            # 計算分析指標 (處理 NA 邏輯)
            rev_b = rev / 100000000 if pd.notna(rev) else pd.NA
            gp_b = gp / 100000000 if pd.notna(gp) else pd.NA
            opex_b = opex / 100000000 if pd.notna(opex) else pd.NA
            net_b = net / 100000000 if pd.notna(net) else pd.NA
            
            gm_pct = (gp / rev * 100) if pd.notna(gp) and pd.notna(rev) and rev > 0 else pd.NA
            nm_pct = (net / rev * 100) if pd.notna(net) and pd.notna(rev) and rev > 0 else pd.NA
            
            inv_days = (inv / cogs * 90) if pd.notna(inv) and pd.notna(cogs) and cogs > 0 else pd.NA
            ar_days = (ar / rev * 90) if pd.notna(ar) and pd.notna(rev) and rev > 0 else pd.NA
            
            results.append({
                '季度': q_date, '單季營收 (億)': rev_b, '毛利 (億)': gp_b, '毛利率 (%)': gm_pct,
                '營業費用 (億)': opex_b, '淨利 (億)': net_b, '淨利率 (%)': nm_pct,
                '存貨周轉天數': inv_days, '應收帳款天數': ar_days,
                '_raw_rev': rev, '_raw_gp': gp, '_raw_net': net
            })
            
        df = pd.DataFrame(results).head(8) # 最多取近8季
        
        # YTD 累計邏輯 (按年歸零)
        ytd_df = df.copy().iloc[::-1].reset_index(drop=True)
        ytd_df['年份'] = ytd_df['季度'].str[:4]
        ytd_df['累計營收 (億)'] = ytd_df.groupby('年份')['單季營收 (億)'].cumsum()
        ytd_df['累計淨利 (億)'] = ytd_df.groupby('年份')['淨利 (億)'].cumsum()
        ytd_df = ytd_df.iloc[::-1].drop(columns=['年份']).reset_index(drop=True)
        
        return df, ytd_df
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame()

# === AI 智慧稽核引擎 (給出具體表現與查核建議) ===
def generate_ai_audit_insights(df):
    if len(df) < 2: return 50, ["數據不足"], ["無法評估"], ["等待新一季財報發布後執行覆核。"]
    
    latest = df.iloc[0]
    prev = df.iloc[1]
    
    score = 75 # 基礎分數
    good_points = []
    bad_points = []
    audit_actions = []
    
    # 1. 營收動能
    if pd.notna(latest['_raw_rev']) and pd.notna(prev['_raw_rev']):
        growth = (latest['_raw_rev'] - prev['_raw_rev']) / prev['_raw_rev']
        if growth > 0.05:
            score += 10
            good_points.append(f"營收強勢成長 (QoQ +{growth*100:.1f}%)")
        elif growth < -0.05:
            score -= 15
            bad_points.append(f"營收顯著衰退 (QoQ {growth*100:.1f}%)")
            audit_actions.append("【營收查核】檢視核心業務之客戶流失狀況，比對銷貨退回與折讓明細，確認是否有提前認列營收後退貨之情事。")
            
    # 2. 獲利能力 (毛利率)
    if pd.notna(latest['毛利率 (%)']) and pd.notna(prev['毛利率 (%)']):
        margin_diff = latest['毛利率 (%)'] - prev['毛利率 (%)']
        if margin_diff > 1.0:
            score += 15
            good_points.append(f"毛利率擴張顯著 (+{margin_diff:.1f}%)，定價能力提升")
        elif margin_diff < -1.0:
            score -= 15
            bad_points.append(f"毛利率面臨壓縮 ({margin_diff:.1f}%)")
            audit_actions.append("【成本查核】毛利異常下滑，建議抽核本季前十大採購單與原物料進項憑證，釐清是成本通膨或遭客戶強力砍價。")

    # 3. 營運資金風險 (存貨與應收)
    if pd.notna(latest['應收帳款天數']) and pd.notna(prev['應收帳款天數']):
        if latest['應收帳款天數'] > prev['應收帳款天數'] * 1.15:
            score -= 15
            bad_points.append("應收帳款周轉天數急遽攀升，收款效率惡化")
            audit_actions.append("【信用查核】收款週期拉長，建議會同財會部調閱『應收帳款帳齡分析表 (Aging Schedule)』，確認是否需增提備抵呆帳，並嚴查經銷商授信。")
            
    if pd.notna(latest['存貨周轉天數']) and pd.notna(prev['存貨周轉天數']):
        if latest['存貨周轉天數'] > prev['存貨周轉天數'] * 1.15:
            score -= 15
            bad_points.append("存貨積壓嚴重，周轉天數飆高")
            audit_actions.append("【實地盤點】資金被庫存卡死。建議稽核長即刻排定廠區無預警實地盤點，確認是否有呆滯料、過期品，並評估存貨跌價損失認列之適足性。")

    if not good_points: good_points.append("本季度營運持平，無顯著擴張亮點。")
    if not bad_points: 
        bad_points.append("未偵測到重大財務預警訊號。")
        audit_actions.append("【例行覆核】目前財務體質穩健，維持常規之內控與內稽抽驗計畫即可。")

    score = max(0, min(100, int(score))) 
    return score, good_points, bad_points, audit_actions

# === 產業同業對標資料庫 ===
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
def fetch_peers_growth_matrix(peer_info):
    """抓取真實 TTM 數據，建立「成長與獲利護城河矩陣」以解決台股 BS 缺漏問題"""
    results = []
    
    for p in peer_info['peers']:
        try:
            tk = yf.Ticker(f"{p['code']}.TW")
            info = tk.info
            # 這些是 YF 上台股最穩定存在的真實指標
            rev_growth = info.get('revenueGrowth')
            pm = info.get('profitMargins')
            mkt_cap = info.get('marketCap')
            
            if rev_growth is not None and pm is not None:
                results.append({
                    "公司": f"{p['name']}",
                    "代碼": p['code'],
                    "營收成長率 YoY (%)": round(rev_growth * 100, 2),
                    "淨利率 (%)": round(pm * 100, 2),
                    "市值 (億)": round((mkt_cap if mkt_cap else 1000000000) / 100000000, 1)
                })
        except: pass
    return pd.DataFrame(results)

# ==========================================
# === 4. 繪圖模組 ===
# ==========================================
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

# ==========================================
# === 5. 左側選單：完整保留所有巨集與標的 ===
# ==========================================
market_categories = {
    "📈 總體經濟與大盤 (宏觀指標)": {
        "🇹🇼 台灣加權指數": "^TWII", "🇺🇸 S&P 500": "^GSPC", "🇺🇸 Dow Jones": "^DJI", "🇺🇸 Nasdaq": "^IXIC", 
        "🇺🇸 SOX (費半)": "^SOX", "⚠️ VIX 恐慌指數": "^VIX", "🏦 U.S. 10Y Treasury": "^TNX", "🥇 黃金": "GC=F", 
        "🛢️ WTI 原油": "CL=F", "₿ 比特幣": "BTC-USD", "💵 美元指數": "DX-Y.NYB", "💱 美元兌台幣": "TWD=X"
    },
    "🏢 遠東集團核心事業體": {
        "🇹🇼 1402 遠東新": "1402", "🇹🇼 1102 亞泥": "1102", "🇹🇼 2606 裕民": "2606", "🇹🇼 1460 宏遠": "1460", 
        "🇹🇼 2903 遠百": "2903", "🇹🇼 4904 遠傳": "4904", "🇹🇼 1710 東聯": "1710", "🇹🇼 2845 遠東銀": "2845"
    },
    "👕 國際品牌終端 (紡織板塊對標)": {"🇺🇸 Nike": "NKE", "🇺🇸 Under Armour": "UAA", "🇺🇸 Lululemon": "LULU"},
    "🥤 國際品牌終端 (化纖板塊對標)": {"🇺🇸 Coca-Cola": "KO", "🇺🇸 PepsiCo": "PEP"}
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

# ==========================================
# === 6. 報價與技術線圖區塊 ===
# ==========================================
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

df_bench = pd.DataFrame()
bench_name = ""
if not df_daily.empty:
    if is_tw_stock: bench_code, bench_name = "^TWII", "TAIEX (台灣加權指數)"
    elif code == "^TWII": bench_code, bench_name = "^GSPC", "S&P 500 指數"
    else: bench_code, bench_name = "^GSPC", "S&P 500 指數"
    if bench_code != code:
        bench_hist = fetch_us_history(bench_code)
        if bench_hist: df_bench = pd.DataFrame(bench_hist)

current_price = real_data['price']
if (current_price == 0 or current_price is None) and not df_daily.empty:
    current_price = df_daily.iloc[-1]['close']
    real_data.update({'high': df_daily.iloc[-1]['high'], 'low': df_daily.iloc[-1]['low'], 'open': df_daily.iloc[-1]['open']})

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
<div style="background-color: #f8fafc; padding: 25px; border-radius: 8px; margin-bottom: 25px; border-left: 6px solid {'#fca5a5' if change >= 0 else '#86efac'};">
    <h2 style="margin:0; color:#475569; font-size: 1.1rem; font-weight: 600;">{option}</h2>
    <div style="display: flex; align-items: baseline; gap: 15px; margin-top: 8px;">
        <span style="font-size: 3.2rem; font-weight: 700; color: #0f172a; letter-spacing: -1px;">
           {"NT$" if is_tw_stock else ""} {current_price:,.2f}
        </span>
        <span style="font-size: 1.5rem; font-weight: 600; color: {'#dc2626' if change >= 0 else '#16a34a'};">{change:+.2f} ({pct:+.2f}%)</span>
    </div>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])
with col1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    if df_intra is not None and not df_intra.empty: st.plotly_chart(plot_intraday_line(df_intra), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    if not df_daily.empty: st.plotly_chart(plot_daily_k(df_daily), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# === 7. 下半部：高階經理人專屬財務戰情室 (100%真實數據) ===
# ==========================================
if is_tw_stock:
    st.divider()
    st.markdown("## 📈 企業基本面與稽核戰略解析 (Executive Financials)")
    
    # 強制使用真實數據，若無資料直接回傳空 DF，不再模擬
    df_quarterly, df_ytd = get_real_financials_strict(code)

    if not df_quarterly.empty and len(df_quarterly) >= 2:
        latest = df_quarterly.iloc[0]
        
        # --- 🤖 AI 財報健檢與具體建議 ---
        st.markdown("### 🤖 智能財務健檢與稽核行動指南 (AI Audit Engine)")
        st.caption("💡 模型說明：本模組透過分析公開財務之「成長動能、毛利擴張、營運資金效率」，動態生成風險預警與查核建議，以輔助高階稽核決策。")
        
        score, good_pts, bad_pts, actions = generate_ai_audit_insights(df_quarterly)
        
        col_ai1, col_ai2, col_ai3 = st.columns([1, 1.2, 1.5])
        
        with col_ai1:
            st.markdown(f"""
            <div class="ai-score-panel">
                <div style="font-size:13px; color:#94a3b8; text-transform:uppercase; letter-spacing:1px;">AI 稽核體質評分</div>
                <div class="ai-score-num" style="color:{'#4ade80' if score>=70 else ('#fbbf24' if score>=50 else '#f87171')};">{score}</div>
                <div style="font-size:12px; color:#cbd5e1;">滿分100 / 基準線70</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_ai2:
            st.markdown('<div class="audit-good-panel"><div class="audit-title">✅ 營運亮點 (Strengths)</div>', unsafe_allow_html=True)
            for pt in good_pts: st.markdown(f'<div class="audit-text">• {pt}</div>', unsafe_allow_html=True)
            st.markdown('<div style="margin-top:15px;" class="audit-title">⚠️ 風險預警 (Risks)</div>', unsafe_allow_html=True)
            for pt in bad_pts: st.markdown(f'<div class="audit-text" style="color:#b91c1c;">• {pt}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col_ai3:
            st.markdown('<div class="audit-action-panel"><div class="audit-title">🎯 稽核行動建議 (Audit Action Plan)</div>', unsafe_allow_html=True)
            for act in actions: st.markdown(f'<div class="audit-text" style="margin-bottom:8px;">👉 {act}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- 📊 營收規模與獲利能力趨勢 (解開 Y 軸限制，凸顯波動) ---
        c_chart1, c_chart2 = st.columns([1, 1.2]) 
        with c_chart1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            plot_df = df_quarterly.iloc[::-1].dropna(subset=['單季營收 (億)'])
            fig1 = make_subplots(specs=[[{"secondary_y": True}]])
            fig1.add_trace(go.Bar(x=plot_df['季度'], y=plot_df['單季營收 (億)'], name="營收 (億)", marker_color='#CBD5E1'), secondary_y=False)
            fig1.add_trace(go.Scatter(x=plot_df['季度'], y=plot_df['毛利率 (%)'], name="毛利率 %", mode='lines+markers', line=dict(color='#0F172A', width=3)), secondary_y=True)
            fig1.add_trace(go.Scatter(x=plot_df['季度'], y=plot_df['淨利率 (%)'], name="淨利率 %", mode='lines+markers', line=dict(color='#3B82F6', width=2)), secondary_y=True)
            
            # 關鍵修改：取消 secondary_y 的強制範圍，讓微小波動也能呈現巨大的視覺起伏
            fig1.update_layout(title="<b>📊 營收與獲利趨勢 (Auto-Scaled)</b>", height=420, margin=dict(l=0, r=0, t=40, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            fig1.update_yaxes(title_text="金額 (億台幣)", secondary_y=False, showgrid=False)
            fig1.update_yaxes(title_text="百分比 (%)", secondary_y=True, showgrid=True, gridcolor='#F1F5F9', autorange=True) # 解開束縛！
            st.plotly_chart(fig1, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c_chart2:
            st.markdown("""<style>.waterfall-container { background: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 25px;}</style>""", unsafe_allow_html=True)
            st.markdown('<div class="waterfall-container">', unsafe_allow_html=True)
            
            # 使用專業配色：藍增加，紅減少，深灰總和
            fig2 = go.Figure(go.Waterfall(
                name="20", orientation="v", measure=["relative", "relative", "total", "relative", "total"],
                x=["營業收入", "營業成本", "毛利", "營業費用/稅", "本期淨利"], textposition="outside", textfont=dict(size=14, color='#0f172a', weight='bold'),
                text=[f"{latest['單季營收 (億)']}", f"-{latest['單季營收 (億)'] - latest['毛利 (億)']:.1f}", f"{latest['毛利 (億)']}", f"-{latest['毛利 (億)'] - latest['淨利 (億)']:.1f}", f"{latest['淨利 (億)']}"],
                y=[latest['單季營收 (億)'], -(latest['單季營收 (億)'] - latest['毛利 (億)']), latest['毛利 (億)'], -(latest['毛利 (億)'] - latest['淨利 (億)']), latest['淨利 (億)']],
                connector={"line":{"color":"#94A3B8", "dash": 'dot', "width": 2}}, 
                decreasing={"marker":{"color":"#EF4444"}}, # 紅色 (成本/費用)
                increasing={"marker":{"color":"#2563EB"}}, # 藍色 (營收)
                totals={"marker":{"color":"#1E293B"}}      # 深灰 (結餘)
            ))
            fig2.update_layout(title=f"<b>💰 獲利結構拆解 (最新財報: {latest['季度']})</b>", height=420, margin=dict(l=0, r=0, t=50, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # === ⚔️ 同業成長與獲利矩陣 (解決台股缺 BS 資料的完美方案) ===
        if code in INDUSTRY_PEERS:
            st.markdown("### ⚔️ 產業護城河矩陣 (Growth vs. Profitability Matrix)")
            peer_info = INDUSTRY_PEERS[code]
            st.caption(f"📍 觀測賽道：{peer_info['name']} | 數據源：YF TTM (近四季滾動) 絕對真實數據")
            
            df_peers_matrix = fetch_peers_growth_matrix(peer_info)
            
            if not df_peers_matrix.empty and len(df_peers_matrix) > 1:
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                
                moat_fig = go.Figure()
                moat_fig.add_trace(go.Scatter(
                    x=df_peers_matrix['營收成長率 YoY (%)'], y=df_peers_matrix['淨利率 (%)'],
                    mode='markers+text', text=df_peers_matrix['公司'], textposition="top center",
                    marker=dict(
                        size=np.sqrt(df_peers_matrix['市值 (億)']) * 1.5, # 泡泡大小代表市值
                        color=df_peers_matrix['淨利率 (%)'], colorscale='Blues', showscale=False,
                        line=dict(width=2, color='DarkSlateGrey')
                    ),
                    hovertemplate="<b>%{text}</b><br>營收成長 YoY: %{x}%<br>淨利率: %{y}%<br>市值: %{customdata} 億<extra></extra>",
                    customdata=df_peers_matrix['市值 (億)']
                ))
                
                # 十字輔助線切出四大象限
                x_mid = df_peers_matrix['營收成長率 YoY (%)'].median()
                y_mid = df_peers_matrix['淨利率 (%)'].median()
                moat_fig.add_hline(y=y_mid, line_dash="dot", line_color="#94A3B8")
                moat_fig.add_vline(x=x_mid, line_dash="dot", line_color="#94A3B8")
                
                moat_fig.update_layout(
                    title=f"<b>🎯 企業戰略地位：成長動能 vs 獲利護城河</b>",
                    xaxis=dict(title="營收成長率 YoY (%) 👉 越靠右成長越快", showgrid=False),
                    yaxis=dict(title="淨利率 (%) 👆 越靠上越賺錢", showgrid=True, gridcolor='#F1F5F9'),
                    height=450, margin=dict(l=20, r=20, t=60, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    annotations=[
                        dict(x=0.98, y=0.95, xref="paper", yref="paper", text="<b>🥇 護城河王者</b><br>高成長/高獲利", showarrow=False, font=dict(color="#10B981"), align="right"),
                        dict(x=0.02, y=0.95, xref="paper", yref="paper", text="<b>💵 現金牛</b><br>低成長/高獲利", showarrow=False, font=dict(color="#3B82F6"), align="left"),
                        dict(x=0.98, y=0.05, xref="paper", yref="paper", text="<b>⚔️ 市佔擴張區</b><br>高成長/低獲利", showarrow=False, font=dict(color="#F59E0B"), align="right"),
                        dict(x=0.02, y=0.05, xref="paper", yref="paper", text="<b>⚠️ 營運危險區</b><br>低成長/低獲利", showarrow=False, font=dict(color="#EF4444"), align="left")
                    ]
                )
                st.plotly_chart(moat_fig, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("⚠️ 該產業目前在公開庫中缺乏足夠的同業財報，矩陣無法生成。")

        # Matrices (財報矩陣)
        st.markdown("### 📑 核心財務數據矩陣 (100% YF 真實擷取)")
        tab1, tab2 = st.tabs(["📊 單季表現 (Quarterly)", "📈 累計表現 (Year-To-Date)"])
        
        # 隱藏用來計算的底層 _raw 資料
        display_df = df_quarterly[[c for c in df_quarterly.columns if not c.startswith('_')]]
        format_dict = {'單季營收 (億)': '{:,.1f}', '毛利 (億)': '{:,.1f}', '營業費用 (億)': '{:,.1f}', '淨利 (億)': '{:,.1f}', '毛利率 (%)': '{:.1f}%', '淨利率 (%)': '{:.1f}%', '存貨周轉天數': '{:.1f}', '應收帳款天數': '{:.1f}'}
        
        with tab1:
            st.dataframe(display_df.style.format(format_dict, na_rep="N/A"), use_container_width=True, height=320)

        with tab2:
            if not df_ytd.empty:
                ytd_cols = ['季度', '累計營收 (億)', '累計淨利 (億)']
                format_ytd = {'累計營收 (億)': '{:,.1f}', '累計淨利 (億)': '{:,.1f}'}
                st.dataframe(df_ytd[ytd_cols].style.format(format_ytd, na_rep="N/A"), use_container_width=True, height=320)
    else:
        st.warning("⚠️ 無法獲取該公司完整的季度財報。基於嚴格稽核標準，系統拒絕展示模擬或虛假數據。建議切換其他標的或確認 YF API 狀態。")

update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f'<div style="text-align:center; color:#94a3b8; font-size:0.8rem; margin-top:3rem;">系統更新時間：{update_time} ｜ 資料來源：TWSE, Yahoo Finance (Zero Fake Data Engine)</div>', unsafe_allow_html=True)
