import streamlit as st
import twstock
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz
import requests
import urllib3
import yfinance as yf
import numpy as np
import os
import pickle
import io

# === 0. 系統層級修復 ===
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
original_request = requests.Session.request
def patched_request(self, method, url, *args, **kwargs):
    kwargs['verify'] = False
    return original_request(self, method, url, *args, **kwargs)
requests.Session.request = patched_request

# ====================== 財務資料 永久保存 ======================
DATA_DIR = "./data"
FIN_FILE = os.path.join(DATA_DIR, "fin_data.pkl")
def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
def load_saved_fin_data():
    if os.path.exists(FIN_FILE):
        try:
            with open(FIN_FILE, "rb") as f:
                return pickle.load(f)
        except:
            return None
    return None
def save_fin_data(df):
    ensure_data_dir()
    try:
        with open(FIN_FILE, "wb") as f:
            pickle.dump(df, f)
        return True
    except:
        return False
def clear_saved_fin_data():
    if os.path.exists(FIN_FILE):
        os.remove(FIN_FILE)
        return True
    return False

# ====================== 財務資料 解析 ======================
@st.cache_data
def parse_fin_excel_files(uploaded_files):
    if not uploaded_files:
        return None
    all_dfs = []
    for uploaded_file in uploaded_files:
        try:
            if uploaded_file.name.lower().endswith('.csv'):
                try:
                    df = pd.read_csv(uploaded_file, encoding='utf-8')
                except UnicodeDecodeError:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, encoding='big5-hkscs')
                dfs = {'Sheet1': df}
            else:
                dfs = pd.read_excel(uploaded_file, sheet_name=None)
               
            for sheet_name, df in dfs.items():
                df = df.copy()
                df.columns = [str(col).strip().replace('\n', '').replace('\r', '').replace(' ', '') for col in df.columns]
               
                col_mapping = {
                    '代號': 'stock_id',
                    '名稱': 'company_name',
                    '年/月': 'date',
                    '存貨及應收帳款/淨值': 'inv_ar_to_equity',
                    '應收帳款週轉次數': 'ar_turnover_times',
                    '總資產週轉次數': 'total_assets_turnover',
                    '平均收帳天數': 'ar_days',
                    '存貨週轉率（次）': 'inv_turnover_times',
                    '存貨週轉率(次)': 'inv_turnover_times',
                    '平均售貨天數': 'inv_days',
                    '固定資產週轉次數': 'fixed_assets_turnover',
                    '淨值週轉率（次）': 'equity_turnover',
                    '應付帳款付現天數': 'ap_days',
                    '淨營業週期（日）': 'net_operating_cycle',
                    '土地/淨值': 'land_to_equity',
                    '固定資產/淨值': 'fixed_assets_to_equity',
                    '利息未收現比率': 'uncollected_interest_ratio',
                    '催收款比率': 'npl_ratio',
                    '資產市占率': 'asset_market_share',
                    '淨值市占率': 'equity_market_share',
                    '存款市占率': 'deposit_market_share',
                    '放款市占率': 'loan_market_share'
                }
                df = df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns})
               
                if 'stock_id' not in df.columns and 'company_name' in df.columns:
                    df['stock_id'] = df['company_name'].astype(str).str.extract(r'(\d{4})')
                if 'stock_id' in df.columns:
                    df['stock_id'] = df['stock_id'].astype(str).str.zfill(4)
               
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'], errors='coerce')
               
                numeric_cols = [
                    'inv_ar_to_equity', 'ar_turnover_times', 'total_assets_turnover', 'ar_days',
                    'inv_turnover_times', 'inv_days', 'fixed_assets_turnover', 'equity_turnover',
                    'ap_days', 'net_operating_cycle',
                    'land_to_equity', 'fixed_assets_to_equity', 'uncollected_interest_ratio',
                    'npl_ratio', 'asset_market_share', 'equity_market_share',
                    'deposit_market_share', 'loan_market_share'
                ]
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
               
                if 'inv_turnover_times' in df.columns:
                    df['inv_days'] = (365 / df['inv_turnover_times']).round(1)
               
                all_dfs.append(df)
        except Exception as e:
            st.warning(f"檔案「{uploaded_file.name}」解析失敗：{str(e)}")
           
    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        sort_cols = [col for col in ['stock_id', 'date'] if col in combined.columns]
        if sort_cols:
            combined = combined.sort_values(sort_cols, ascending=[True] * len(sort_cols)).reset_index(drop=True)
        return combined
    return None

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
if not check_password():
    st.stop()

# === 2. 核心 UI 樣式與 CSS 注入 ===
st.markdown("""
    <style>
        html, body, [class*="css"] { font-family: 'Noto Sans TC', 'Microsoft JhengHei', sans-serif !important; }
        .main-title { font-size: 2.2rem; font-weight: 800; color: #1e293b; text-align: center; margin: 1rem 0; letter-spacing: 1px;}
        .sub-title { font-size: 1rem; color: #64748b; text-align: center; margin-bottom: 2rem; font-weight: 500;}
        .score-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 15px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);}
        .score-card-title { font-size: 14px; color: #64748b; font-weight: 600; margin-bottom: 5px;}
        .score-card-value { font-size: 36px; font-weight: 800; color: #0f172a;}
        .highlight-card { border: 2px solid #3b82f6; background: #f8fafc;}
       
        [data-testid="stFileUploadDropzone"] > div > span { display: none !important; }
        [data-testid="stFileUploadDropzone"] > div::after {
            content: "📤 點擊或拖曳上傳財報/銀行同業檔案 (支援 xlsx, csv)";
            display: block;
            font-weight: 600;
            color: #475569;
            font-size: 15px;
            margin-top: 10px;
        }
        [data-testid="stFileUploadDropzone"] small { display: none !important; }
    </style>
""", unsafe_allow_html=True)
st.markdown('<div class="main-title">遠東集團 (Far Eastern Group)</div><div class="sub-title">聯合稽核總部 ｜ 戰略決策儀表板</div>', unsafe_allow_html=True)

# ====================== 【新增】台灣加權指數緊急警示系統 ======================
@st.cache_data(ttl=60)   # 每 60 秒自動更新一次
def get_twii_current_price():
    """優先使用 twstock，失敗則 fallback yfinance"""
    try:
        real = twstock.realtime.get("^TWII")
        if real.get('success'):
            latest = real['realtime'].get('latest_trade_price')
            if latest and latest != '-':
                return float(latest), True   # True 表示即時價格
    except:
        pass
    # fallback 到 yfinance
    try:
        tk = yf.Ticker("^TWII")
        price = tk.fast_info.last_price
        return price, False
    except:
        return None, False

# 取得當前指數
twii_price, is_realtime = get_twii_current_price()

# 若低於 33500 點，立即顯示紅色緊急警示
if twii_price is not None and twii_price < 33500:
    status_text = "🟢 即時" if is_realtime else "⏰ 非交易時間（最新收盤）"
    drop_points = 33500 - twii_price
    html_alert = f"""
    <div style="background: linear-gradient(90deg, #ef4444, #b91c1c); 
                color: white; 
                padding: 25px 30px; 
                border-radius: 16px; 
                margin: 20px 0 30px 0; 
                box-shadow: 0 10px 25px rgba(239, 68, 68, 0.4);
                text-align: center; 
                animation: pulse 2s infinite;">
        <h2 style="margin:0; font-size: 2.1rem; font-weight: 900; letter-spacing: -1px;">
            ⚠️ 緊急警示！台灣加權指數已跌破 33500 點 ⚠️
        </h2>
        <div style="font-size: 1.6rem; margin: 15px 0;">
            目前指數：<strong>{twii_price:,.0f}</strong> 點　　|　　{status_text}
        </div>
        <div style="font-size: 1.3rem; background: rgba(255,255,255,0.2); display: inline-block; padding: 8px 24px; border-radius: 9999px;">
            跌破 {drop_points:,.0f} 點　　🔴 請立即關注外資流向與半導體族群風險
        </div>
    </div>
    <style>
        @keyframes pulse {{
            0% {{ opacity: 1; }}
            50% {{ opacity: 0.85; }}
            100% {{ opacity: 1; }}
        }}
    </style>
    """
    st.markdown(html_alert, unsafe_allow_html=True)

# === 3. 深度戰略連動註解庫 ===
MACRO_IMPACT = {
    "🇹🇼 台灣加權指數": "台灣加權指數為台灣整體經濟及半導體產業景氣的綜合指標。主要與台積電等科技巨頭連動，可作為評估外資資金流向及國內資本市場活力的關鍵參考。",
    "🇺🇸 S&P 500": "S&P 500 指數涵蓋美國前 500 大企業，代表美國實體經濟的全貌。其涵蓋多樣產業，為全球長期資金配置及美股市場多空趨勢判斷的基準指標。",
    "🇺🇸 Dow Jones": "道瓊工業指數涵蓋 30 家歷史悠久的美國藍籌企業（涵蓋工業、金融等領域）。有助於評估美國傳統經濟基礎的穩健性，並對傳統企業獲利能力高度敏感。",
    "🇺🇸 Nasdaq": "納斯達克指數為全球科技創新的領先指標，聚集微軟、蘋果等科技巨頭。直接反映市場對 AI、軟硬體等高科技領域資本支出的成長預期。",
    "🇺🇸 SOX (費半)": "費城半導體指數為全球半導體產業鏈的核心指標，涵蓋晶片設計至設備製造等環節，可精準預測電子業庫存循環及終端需求趨勢。",
    "⚠️ VIX 恐慌指數": "VIX 恐慌指數用以衡量市場投資人的恐慌程度。當指數大幅上升時，顯示投資人預期未來市場波動加劇，常伴隨股市下跌，為重要的避險指標。",
    "🏦 U.S. 10Y Treasury": "美國 10 年期公債殖利率為全球資金定價的無風險基準。殖利率上升會吸引資金離開股市並提高企業融資成本，為評估科技股估值及通膨預期的關鍵指標。",
    "🥇 黃金": "黃金為市場動盪時的資金避險資產。當通膨失控或地緣政治危機發生時，金價通常上漲，反映市場對法定貨幣的不信任。",
    "🛢️ WTI 原油": "WTI 原油為實體工業與運輸業的關鍵能源指標。油價上漲會提高全球製造業成本並引發通膨壓力，為評估美國工業活動及通膨趨勢的重要參考。",
    "🛢️ 布蘭特原油 (Brent)": "布蘭特原油為全球國際貿易的基準油價。對中東衝突及 OPEC+ 減產等事件高度敏感，直接影響歐洲與亞洲的能源成本。",
    "🔥 天然氣 (Natural Gas)": "天然氣為重工業運轉及冬季供暖的核心能源。價格受極端氣候及地緣政治事件影響顯著，上漲時將衝擊高耗能產業（如石化、水泥）的獲利能力。",
    "🚢 航運運價指標 (BDRY)": "BDRY 航運運價指數反映全球原物料海上運輸需求。運價上漲表示基礎建設需求強勁，為實體經濟擴張的領先指標。",
    "₿ 比特幣": "比特幣為數位時代的高風險資產。價格波動劇烈，並與全球過剩資金流向高度相關，為市場投機情緒的領先指標。",
    "💵 美元指數": "美元指數衡量美元相對於全球主要貨幣的強弱。強勢美元會導致熱錢撤出新興市場（如台灣），雖有利出口業，但會增加進口原物料成本。",
    "💱 美元兌台幣": "美元兌台幣匯率為台灣出口企業獲利的重要因素。台幣貶值可使電子代工及紡織業獲得匯兌收益，但會提高進口物價。"
}

# === 4. 板塊分類字典 ===
market_categories = {
    "📈 總體經濟與大盤 (宏觀指標)": {
        "🇹🇼 台灣加權指數": "^TWII", "🇺🇸 S&P 500": "^GSPC", "🇺🇸 Dow Jones": "^DJI", "🇺🇸 Nasdaq": "^IXIC",
        "🇺🇸 SOX (費半)": "^SOX", "⚠️ VIX 恐慌指數": "^VIX", "🏦 U.S. 10Y Treasury": "^TNX", "🥇 黃金": "GC=F",
        "🛢️ WTI 原油": "CL=F", "🛢️ 布蘭特原油 (Brent)": "BZ=F", "🔥 天然氣 (Natural Gas)": "NG=F",
        "🚢 航運運價指標 (BDRY)": "BDRY", "₿ 比特幣": "BTC-USD", "💵 美元指數": "DX-Y.NYB", "💱 美元兌台幣": "TWD=X"
    },
    "🏢 遠東集團核心事業體": {
        "👕 1402 遠東新": "1402", "🏗️ 1102 亞泥": "1102", "🚢 2606 裕民": "2606", "🧵 1460 宏遠": "1460",
        "🛍️ 2903 遠百": "2903", "📱 4904 遠傳": "4904", "🧪 1710 東聯": "1710", "🏦 2845 遠東銀": "2845"
    },
    "👟 國際品牌終端 (紡織板塊對標)": {"🇺🇸 Nike": "NKE", "🇺🇸 Under Armour": "UAA", "🇺🇸 Lululemon": "LULU"},
    "🥤 國際品牌終端 (化纖板塊對標)": {"🇺🇸 Coca-Cola": "KO", "🇺🇸 PepsiCo": "PEP"}
}

# === 擴充：加入銀行業的外部競爭對手 ===
external_peers = {
    '1402': ['1409', '1718', '1464'],
    '1460': ['1409', '1718', '1464'],
    '1710': ['1718'],
    '1102': ['1101', '1103', '1104', '1108', '1109', '1110', '2504'],
    '2606': ['2605', '5608', '2617', '2612', '2641'],
    '2903': [],
    '4904': ['2412', '3045'],
    '2845': ['2801', '2812', '2838', '2897', '2834', '2809', '2836', '2849', '5876']
}
company_name_dict = {
    '1402': '遠東新', '1409': '新纖', '1464': '得力', '1718': '中纖',
    '1101': '台泥', '1103': '嘉泥', '1104': '環泥', '1108': '幸福',
    '1109': '信大', '1110': '東泥', '2504': '國產',
    '2605': '新興', '5608': '四維航', '2617': '台航', '2612': '中航', '2641': '正德',
    '2412': '中華電', '3045': '台灣大',
    '1460': '宏遠', '1710': '東聯', '2903': '遠百', '4904': '遠傳', '2845': '遠東銀',
    '2801': '彰銀', '2812': '台中銀', '2838': '聯邦銀', '2897': '王道銀行',
    '2834': '臺企銀', '2809': '京城銀', '2836': '高雄銀', '2849': '安泰銀', '5876': '上海商銀'
}

# === 5. API 與真實資料抓取模組 ===
@st.cache_data(ttl=3600)
def fetch_history_yf(stock_code, is_tw=False):
    try:
        symbol = f"{stock_code}.TW" if is_tw else stock_code
        tk = yf.Ticker(symbol)
        hist = tk.history(period="6mo")
        if hist.empty and is_tw:
            symbol = f"{stock_code}.TWO"
            tk = yf.Ticker(symbol)
            hist = tk.history(period="6mo")
           
        data_list = []
        for idx, row in hist.iterrows():
            data_list.append({
                'date': idx.strftime('%Y-%m-%d'),
                'volume': float(row['Volume']),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close'])
            })
        return data_list
    except:
        return []

@st.cache_data(ttl=300)
def get_intraday_chart_data(stock_code, is_us_source=False):
    try:
        ticker = yf.Ticker(stock_code if is_us_source else f"{stock_code}.TW")
        df = ticker.history(period="1d", interval="1m")
        if df.empty:
            df = ticker.history(period="5d", interval="5m")
            if not df.empty:
                df = df[df.index.date == df.index[-1].date()]
        return df if not df.empty else None
    except: return None

def plot_daily_k(df):
    if df.empty: return None
    df = df.copy()
    df.set_index(pd.to_datetime(df['date']), inplace=True)
    df = df.tail(120)
   
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#ef4444', increasing_fillcolor='#ef4444',
        decreasing_line_color='#22c55e', decreasing_fillcolor='#22c55e',
        name="日K"
    )])
   
    fig.update_layout(
        title="<b>📊 歷史價格走勢 (近半年)</b>",
        xaxis_rangeslider_visible=False,
        height=380,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff'
    )
    fig.update_xaxes(
        showgrid=True, gridwidth=1, gridcolor='#f1f5f9',
        rangebreaks=[dict(bounds=["sat", "mon"])]
    )
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

# === 6. 左側選單 ===
with st.sidebar:
    st.header("🎯 戰略監控目標")
    st.subheader("📤 財務數據資料匯入")
   
    uploaded_files = st.file_uploader("上傳財報檔案", type=["xlsx", "xls", "csv"], accept_multiple_files=True, label_visibility="collapsed")
   
    if uploaded_files:
        with st.spinner("🔄 正在解析並保存資料..."):
            fin_df = parse_fin_excel_files(uploaded_files)
            if fin_df is not None and not fin_df.empty:
                st.session_state['fin_data'] = fin_df
                if save_fin_data(fin_df):
                    st.success("✅ 財務資料已成功上傳並保存")
    else:
        if 'fin_data' not in st.session_state:
            saved = load_saved_fin_data()
            if saved is not None:
                st.session_state['fin_data'] = saved
                st.success("✅ 已自動載入保存的財務資料")
               
    if st.button("🗑️ 清除保存的財務資料"):
        if clear_saved_fin_data():
            st.session_state.pop('fin_data', None)
            st.success("✅ 已清除保存資料")
            st.rerun()
           
    st.markdown("---")
    selected_category = st.selectbox("板塊分類", list(market_categories.keys()))
    st.markdown("---")
    options_dict = market_categories[selected_category]
    option = st.radio("監控標的", list(options_dict.keys()))
    code = options_dict[option]
    is_tw_stock = code.isdigit()

# === 7. 價格顯示、圖表 ===
real_data = {'price': 0, 'high': '-', 'low': '-', 'open': '-', 'volume': '-'}
if is_tw_stock:
    try:
        real = twstock.realtime.get(code)
        if real['success']:
            info = real['realtime']
            latest = float(info['latest_trade_price']) if info['latest_trade_price'] != '-' else (float(info['open']) if info['open'] != '-' else 0.0)
            real_data.update({'price': latest, 'high': info.get('high', '-'), 'low': info.get('low', '-'), 'open': info.get('open', '-'), 'volume': info.get('accumulate_trade_volume', '0')})
    except: pass
    hist_data = fetch_history_yf(code, is_tw=True)
else:
    try:
        tk = yf.Ticker(code)
        fi = tk.fast_info
        real_data.update({'price': fi.last_price, 'open': fi.open, 'high': fi.day_high, 'low': fi.day_low, 'volume': f"{int(fi.last_volume):,}"})
    except: pass
    hist_data = fetch_history_yf(code, is_tw=False)

df_daily = pd.DataFrame(hist_data) if hist_data else pd.DataFrame()
df_intra = get_intraday_chart_data(code, is_us_source=not is_tw_stock)
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
if selected_category == "📈 總體經濟與大盤 (宏觀指標)" and option in MACRO_IMPACT:
    exp_text = MACRO_IMPACT[option]
    html_payload = f"""
    <div style="background-color: #ffffff; padding: 20px 25px; border-radius: 8px; border-left: 5px solid #3b82f6; margin-top: 10px; margin-bottom: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
        <div style="font-size: 16px; color: #1e293b; line-height: 1.8; font-weight: 500; text-align: justify;">
            {exp_text}
        </div>
    </div>
    """
    st.markdown(html_payload.replace('\n', ''), unsafe_allow_html=True)
col1, col2 = st.columns([1, 1])
with col1:
    if df_intra is not None and not df_intra.empty: st.plotly_chart(plot_intraday_line(df_intra), use_container_width=True)
with col2:
    if not df_daily.empty: st.plotly_chart(plot_daily_k(df_daily), use_container_width=True)

# === 8. 財務健檢與同業對標分析 ===
if is_tw_stock:
    st.divider()
    fin_df = st.session_state.get('fin_data', None)
   
    if fin_df is not None and not fin_df.empty:
        peer_codes = external_peers.get(str(code), [])
        all_ids = [str(code)] + peer_codes
        peer_dict = {pid: company_name_dict.get(pid, pid) for pid in all_ids}
        latest_data = {}
        data_date_str = "最新期數"
        for pid in all_ids:
            c_df = fin_df[fin_df['stock_id'] == pid].sort_values('date', ascending=False)
            if not c_df.empty:
                latest_data[pid] = c_df.iloc[0]
        if str(code) in latest_data:
            latest_date_val = latest_data[str(code)].get('date')
            if pd.notna(latest_date_val):
                data_date_str = latest_date_val.strftime('%Y-%m')
        st.markdown(f"## 📊 財務健檢與同業對標分析 <span style='font-size: 1rem; color: #64748b; font-weight: 500;'>（資料期數：{data_date_str}）</span>", unsafe_allow_html=True)
        current_company_name = peer_dict.get(str(code), f"公司 {code}")
        st.markdown(f"### 🔍 目前分析主體：**{current_company_name} ({code})**")
        is_bank = (str(code) in ['2845'] or str(code) in external_peers.get('2845', []))
       
        if is_bank:
            indicators_dict = {
                'land_to_equity': {'name': '土地/淨值', 'better': 'lower'},
                'fixed_assets_to_equity': {'name': '固定資產/淨值', 'better': 'lower'},
                'uncollected_interest_ratio': {'name': '利息未收現比率', 'better': 'lower'},
                'npl_ratio': {'name': '催收款比率', 'better': 'lower'}
            }
            optional_bank_metrics = {
                'asset_market_share': {'name': '資產市占率', 'better': 'higher'},
                'equity_market_share': {'name': '淨值市占率', 'better': 'higher'},
                'deposit_market_share': {'name': '存款市占率', 'better': 'higher'},
                'loan_market_share': {'name': '放款市占率', 'better': 'higher'}
            }
            for k, v in optional_bank_metrics.items():
                if k in fin_df.columns and not fin_df[k].isna().all():
                    indicators_dict[k] = v
        else:
            indicators_dict = {
                'inv_ar_to_equity': {'name': '存貨及應收帳款/淨值', 'better': 'lower'},
                'ar_turnover_times': {'name': '應收帳款週轉次數', 'better': 'higher'},
                'total_assets_turnover': {'name': '總資產週轉次數', 'better': 'higher'},
                'ar_days': {'name': '平均收帳天數', 'better': 'lower'},
                'inv_turnover_times': {'name': '存貨週轉率', 'better': 'higher'},
                'inv_days': {'name': '平均售貨天數', 'better': 'lower'},
                'fixed_assets_turnover': {'name': '固定資產週轉次數', 'better': 'higher'},
                'equity_turnover': {'name': '淨值週轉率', 'better': 'higher'},
                'ap_days': {'name': '應付帳款付現天數', 'better': 'lower'},
                'net_operating_cycle': {'name': '淨營業週期', 'better': 'lower'}
            }
        industry_avg = {}
        for key in indicators_dict.keys():
            vals = [latest_data[pid].get(key) for pid in latest_data if pd.notna(latest_data[pid].get(key))]
            industry_avg[key] = np.mean(vals) if vals else np.nan
        scores = {}
        for pid, data in latest_data.items():
            score = 0
            valid_metrics_count = 0
            for key, info in indicators_dict.items():
                val = data.get(key)
                avg = industry_avg.get(key)
                if pd.notna(val) and pd.notna(avg):
                    valid_metrics_count += 1
                    if info['better'] == 'higher' and val >= avg:
                        score += 10
                    elif info['better'] == 'lower' and val <= avg:
                        score += 10
            final_score = int((score / (valid_metrics_count * 10)) * 100) if valid_metrics_count > 0 else 0
            scores[pid] = final_score
        st.markdown("#### 🏆 經營能力綜合評分比較 (滿分 100 分)")
        cols = st.columns(len(latest_data))
        for i, (pid, score) in enumerate(scores.items()):
            comp_name = peer_dict.get(pid, pid)
            is_current = (pid == str(code))
            highlight_class = "highlight-card" if is_current else ""
            color = "#22c55e" if score >= 60 else "#ef4444"
            with cols[i]:
                st.markdown(f"""
                <div class="score-card {highlight_class}">
                    <div class="score-card-title">{comp_name} ({pid})</div>
                    <div class="score-card-value" style="color: {color};">{score}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 📝 最新關鍵指標明細 (原始數據)")
        table_data = {"指標": [info['name'] for info in indicators_dict.values()]}
        for pid in all_ids:
            if pid in latest_data:
                c_data = latest_data[pid]
                col_name = f"{peer_dict[pid]} ({pid})"
                table_data[col_name] = [
                    round(c_data.get(k, np.nan), 2) if pd.notna(c_data.get(k)) else "-"
                    for k in indicators_dict.keys()
                ]
        metrics_df = pd.DataFrame(table_data)
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)
        st.markdown("#### 🎯 營運雙核心矩陣")
       
        if is_bank:
            x_metric = 'uncollected_interest_ratio'
            y_metric = 'npl_ratio'
            x_title = "利息未收現比率 (%) ➔ 越低越好"
            y_title = "催收款比率 (%) ➔ 越低越好"
            quadrant_caption = "左下角象限代表「利息收現狀況佳」且「資產品質優良 (催收款少)」，為最佳營運狀態。"
            hover_x_name = "利息未收現比率"
            hover_y_name = "催收款比率"
        else:
            x_metric = 'inv_turnover_times'
            y_metric = 'ar_turnover_times'
            x_title = "存貨週轉率 (次) ➔ 越高越好"
            y_title = "應收帳款週轉次數 (次) ➔ 越高越好"
            quadrant_caption = "右上角象限代表「存貨去化快」且「帳款回收快」，為最佳營運狀態。"
            hover_x_name = "存貨週轉率"
            hover_y_name = "應收帳款週轉"
           
        fig_xy = go.Figure()
        for pid in all_ids:
            if pid in latest_data:
                data = latest_data[pid]
                x_val = data.get(x_metric, np.nan)
                y_val = data.get(y_metric, np.nan)
                if pd.notna(x_val) and pd.notna(y_val):
                    is_target = (pid == str(code))
                    fig_xy.add_trace(go.Scatter(
                        x=[x_val], y=[y_val],
                        mode='markers+text',
                        name=peer_dict[pid],
                        text=[peer_dict[pid]],
                        textposition="top center",
                        textfont=dict(size=14, color="#1e293b" if not is_target else "#ef4444", weight="bold" if is_target else "normal"),
                        marker=dict(size=24 if is_target else 18, color='#ef4444' if is_target else '#94a3b8', line=dict(width=2, color='white'), opacity=0.9),
                        hovertemplate=f"<b>{peer_dict[pid]}</b><br>{hover_x_name}: %{{x:.2f}}<br>{hover_y_name}: %{{y:.2f}}<extra></extra>"
                    ))
       
        fig_xy.update_layout(height=500, plot_bgcolor='#f8fafc', paper_bgcolor='#ffffff', margin=dict(l=40,r=40,t=40,b=40),
                              xaxis=dict(title=x_title, gridcolor="white", zerolinecolor="#cbd5e1", zerolinewidth=2),
                              yaxis=dict(title=y_title, gridcolor="white", zerolinecolor="#cbd5e1", zerolinewidth=2),
                              showlegend=False)
        st.plotly_chart(fig_xy, use_container_width=True)
        st.caption(quadrant_caption)
        st.markdown("#### 📈 歷年營運效率趨勢對標")
        trend_metric = st.selectbox("請選擇要深入剖析的戰略指標", options=list(indicators_dict.keys()), format_func=lambda x: indicators_dict[x]['name'])
        fenc_df = fin_df[fin_df['stock_id'] == str(code)].sort_values('date', ascending=True).dropna(subset=['date', trend_metric])
        fenc_df['pct_change'] = fenc_df[trend_metric].pct_change() * 100
        peer_df = fin_df[fin_df['stock_id'].isin(peer_codes)].dropna(subset=['date', trend_metric])
        peer_avg_df = peer_df.groupby('date')[trend_metric].mean().reset_index().rename(columns={trend_metric: 'peer_avg'})
        merged_df = pd.merge(fenc_df[['date', trend_metric, 'pct_change']], peer_avg_df, on='date', how='inner').tail(8)
        if not merged_df.empty:
            x_labels = merged_df['date'].dt.strftime('%Y-%m')
            text_annotations = []
            for _, row in merged_df.iterrows():
                val = row[trend_metric]
                pct = row['pct_change']
                if pd.isna(pct):
                    text_annotations.append(f"{val:.2f}")
                elif pct > 0:
                    text_annotations.append(f"{val:.2f}<br>▲ {pct:.1f}%")
                elif pct < 0:
                    text_annotations.append(f"{val:.2f}<br>▼ {abs(pct):.1f}%")
                else:
                    text_annotations.append(f"{val:.2f}<br>持平")
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Bar(x=x_labels, y=merged_df[trend_metric], name=current_company_name, marker_color='#ef4444', text=text_annotations, textposition='outside'))
            fig_trend.add_trace(go.Bar(x=x_labels, y=merged_df['peer_avg'], name='外部同業平均', marker_color='#cbd5e1', text=[f"{v:.2f}" for v in merged_df['peer_avg']], textposition='outside'))
            fig_trend.update_layout(barmode='group', height=500, plot_bgcolor='#ffffff', paper_bgcolor='#ffffff',
                                    xaxis=dict(title="時間期數"), yaxis=dict(title=indicators_dict[trend_metric]['name']),
                                    legend=dict(orientation="h", y=1.05, x=0.5))
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("資料筆數不足以繪製歷史趨勢，請確認上傳的財報包含足夠的歷史期數。")
    else:
        st.info("請先上傳財務/銀行同業資料以啟用分析功能")

update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f'<div style="text-align:center; color:#94a3b8; font-size:0.8rem; margin-top:3rem;">系統更新時間：{update_time} ｜ 資料來源：內部財報系統（永久保存）</div>', unsafe_allow_html=True)
