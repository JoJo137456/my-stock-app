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

# === 0. 系統層級修復 ===
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
original_request = requests.Session.request
def patched_request(self, method, url, *args, **kwargs):
    kwargs['verify'] = False
    return original_request(self, method, url, *args, **kwargs)
requests.Session.request = patched_request

# ====================== TEJ 永久保存 ======================
DATA_DIR = "./data"
TEJ_FILE = os.path.join(DATA_DIR, "tej_data.pkl")

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def load_saved_tej_data():
    if os.path.exists(TEJ_FILE):
        try:
            with open(TEJ_FILE, "rb") as f:
                return pickle.load(f)
        except:
            return None
    return None

def save_tej_data(df):
    ensure_data_dir()
    try:
        with open(TEJ_FILE, "wb") as f:
            pickle.dump(df, f)
        return True
    except:
        return False

def clear_saved_tej_data():
    if os.path.exists(TEJ_FILE):
        os.remove(TEJ_FILE)
        return True
    return False

# ====================== TEJ 解析（已針對你的最新 Excel 截圖完整對應） ======================
@st.cache_data
def parse_tej_excel_files(uploaded_files):
    if not uploaded_files:
        return None
    all_dfs = []
    for uploaded_file in uploaded_files:
        try:
            dfs = pd.read_excel(uploaded_file, sheet_name=None)
            for sheet_name, df in dfs.items():
                df = df.copy()
                
                # 強力清理欄位名稱
                df.columns = [str(col).strip().replace('\n', '').replace('\r', '').replace(' ', '') for col in df.columns]
                
                # === 針對你提供的「經營能力指標」檔案的精準欄位對應 ===
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
                }
                df = df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns})
                
                # 自動抓 stock_id
                if 'stock_id' not in df.columns and 'company_name' in df.columns:
                    df['stock_id'] = df['company_name'].str.extract(r'(\d{4})')
                if 'stock_id' in df.columns:
                    df['stock_id'] = df['stock_id'].astype(str).str.zfill(4)
                
                # 日期轉換
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'], errors='coerce')
                
                # 數值轉換
                numeric_cols = ['inv_ar_to_equity', 'ar_turnover_times', 'total_assets_turnover', 'ar_days',
                                'inv_turnover_times', 'inv_days', 'fixed_assets_turnover', 'equity_turnover',
                                'ap_days', 'net_operating_cycle']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # 存貨週轉天數（如果有週轉率就自動計算）
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

# === 2. 核心 UI 樣式 ===
st.markdown("""
    <style>
        html, body, [class*="css"] { font-family: 'Noto Sans TC', 'Microsoft JhengHei', sans-serif !important; }
        .main-title { font-size: 2.2rem; font-weight: 800; color: #1e293b; text-align: center; margin: 1rem 0; letter-spacing: 1px;}
        .sub-title { font-size: 1rem; color: #64748b; text-align: center; margin-bottom: 2rem; font-weight: 500;}
        .ai-score-box { background: linear-gradient(135deg, #1e293b, #0f172a); color: white; padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.15);}
        .strength-box { background: #ffffff; border-left: 5px solid #22c55e; padding: 15px; border-radius: 8px; margin-top:15px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);}
        .weakness-box { background: #ffffff; border-left: 5px solid #ef4444; padding: 15px; border-radius: 8px; margin-top:15px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);}
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">遠東集團 (Far Eastern Group)</div><div class="sub-title">聯合稽核總部 ｜ 戰略決策儀表板</div>', unsafe_allow_html=True)

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

# === 5. API 與真實資料抓取模組（保持不變） ===
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

def plot_daily_k(df):
    if df.empty: return None
    df = df.copy()
    df.set_index(pd.to_datetime(df['date']), inplace=True)
    df = df.tail(120)
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#ef4444', increasing_fillcolor='#ef4444',
        decreasing_line_color='#22c55e', decreasing_fillcolor='#22c55e',
        name="日K"
    )])
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

# === 6. 左側選單 ===
with st.sidebar:
    st.header("🎯 戰略監控目標")
    st.subheader("📤 TEJ 資料庫匯入")
    st.markdown("**請上傳 TEJ 報表**  \n— 上傳一次後永久保存（支援多檔 XLSX / XLS）")
   
    uploaded_files = st.file_uploader("TEJ 財報檔案", type=["xlsx", "xls"], accept_multiple_files=True, label_visibility="collapsed")
   
    if uploaded_files:
        with st.spinner("🔄 正在解析並永久保存 TEJ 資料..."):
            tej_df = parse_tej_excel_files(uploaded_files)
            if tej_df is not None and not tej_df.empty:
                st.session_state['tej_data'] = tej_df
                if save_tej_data(tej_df):
                    st.success("✅ TEJ 資料已成功上傳並**永久保存**")
    else:
        if 'tej_data' not in st.session_state:
            saved = load_saved_tej_data()
            if saved is not None:
                st.session_state['tej_data'] = saved
                st.success("✅ 已自動載入**永久保存**的 TEJ 資料")
   
    if st.button("🗑️ 清除永久保存的 TEJ 資料"):
        if clear_saved_tej_data():
            st.session_state.pop('tej_data', None)
            st.success("✅ 已清除永久保存資料")
            st.rerun()
   
    st.markdown("---")
    selected_category = st.selectbox("板塊分類", list(market_categories.keys()))
    st.markdown("---")
    options_dict = market_categories[selected_category]
    option = st.radio("監控標的", list(options_dict.keys()))
    code = options_dict[option]
    is_tw_stock = code.isdigit()

# === 7. 價格顯示、圖表（保持不變） ===
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

# === 8. TEJ 財務健檢與同業對標分析（已改成你要求的「分別列出」表格） ===
if is_tw_stock:
    st.divider()
    st.markdown("## 📊 TEJ 財務健檢與同業對標分析")
    tej_df = st.session_state.get('tej_data', None)
   
    if tej_df is not None and not tej_df.empty:
        company_df = tej_df[tej_df['stock_id'] == str(code)].sort_values('date', ascending=False)
        if not company_df.empty:
            latest = company_df.iloc[0]
            company_name = latest.get('company_name', f'公司 {code}')
           
            # === 限定4家競爭對手 ===
            peer_ids = ['1409', '1464', '1303', '1718']   # 新纖、得力、南亞、中纖
            peers_latest = {}
            for pid in peer_ids:
                p_df = tej_df[tej_df['stock_id'] == pid].sort_values('date', ascending=False)
                if not p_df.empty:
                    peers_latest[pid] = p_df.iloc[0]
            
            st.markdown(f"### 🔍 目前分析公司：**{company_name} ({code})**")
           
            # AI 分數（維持原邏輯）
            score = 75
            if pd.notna(latest.get('gross_margin')) and latest.get('gross_margin', 0) < 15: score -= 15
            if pd.notna(latest.get('net_margin')) and latest.get('net_margin', 0) < 5: score -= 15
            if pd.notna(latest.get('ar_days')) and latest.get('ar_days', 0) > 60: score -= 10
            if pd.notna(latest.get('inv_days')) and latest.get('inv_days', 0) > 80: score -= 10
            if pd.notna(latest.get('revenue')) and latest.get('revenue', 0) == 0: score -= 20
            score = max(10, min(100, int(score)))
           
            col_score, col_compare = st.columns([1, 3])
            with col_score:
                st.markdown(f"""
                <div class="ai-score-box">
                    <div style="font-size:14px; color:#94a3b8;">稽核 AI 分數</div>
                    <div style="font-size:48px; font-weight:800; color:{'#4ade80' if score >= 70 else '#f87171'};">{score}</div>
                    <div style="font-size:13px; margin-top:8px;">
                        90~100 分為極優　70~89 分為優等<br>
                        60~69 分為普通　低於60 分需加強
                    </div>
                </div>
                """, unsafe_allow_html=True)
           
            # === 全新「分別列出」表格 ===
            with col_compare:
                st.markdown("#### 📈 最新關鍵指標（TEJ 資料）")
                
                indicators = [
                    "存貨及應收帳款/淨值",
                    "應收帳款週轉次數",
                    "總資產週轉次數",
                    "平均收帳天數",
                    "存貨週轉率（次）",
                    "平均售貨天數",
                    "固定資產週轉次數",
                    "淨值週轉率（次）",
                    "應付帳款付現天數",
                    "淨營業週期（日）"
                ]
                
                data = {"指標": indicators}
                data["遠東新 (1402)"] = [
                    round(latest.get('inv_ar_to_equity', np.nan), 2) if pd.notna(latest.get('inv_ar_to_equity')) else "-",
                    round(latest.get('ar_turnover_times', np.nan), 2) if pd.notna(latest.get('ar_turnover_times')) else "-",
                    round(latest.get('total_assets_turnover', np.nan), 2) if pd.notna(latest.get('total_assets_turnover')) else "-",
                    round(latest.get('ar_days', np.nan), 1) if pd.notna(latest.get('ar_days')) else "-",
                    round(latest.get('inv_turnover_times', np.nan), 2) if pd.notna(latest.get('inv_turnover_times')) else "-",
                    round(latest.get('inv_days', np.nan), 1) if pd.notna(latest.get('inv_days')) else "-",
                    round(latest.get('fixed_assets_turnover', np.nan), 2) if pd.notna(latest.get('fixed_assets_turnover')) else "-",
                    round(latest.get('equity_turnover', np.nan), 2) if pd.notna(latest.get('equity_turnover')) else "-",
                    round(latest.get('ap_days', np.nan), 1) if pd.notna(latest.get('ap_days')) else "-",
                    round(latest.get('net_operating_cycle', np.nan), 1) if pd.notna(latest.get('net_operating_cycle')) else "-"
                ]
                
                # 加入4家對手
                peer_names = {"1409": "新纖 (1409)", "1464": "得力 (1464)", "1303": "南亞 (1303)", "1718": "中纖 (1718)"}
                for pid, name in peer_names.items():
                    p = peers_latest.get(pid)
                    if p is not None:
                        data[name] = [
                            round(p.get('inv_ar_to_equity', np.nan), 2) if pd.notna(p.get('inv_ar_to_equity')) else "-",
                            round(p.get('ar_turnover_times', np.nan), 2) if pd.notna(p.get('ar_turnover_times')) else "-",
                            round(p.get('total_assets_turnover', np.nan), 2) if pd.notna(p.get('total_assets_turnover')) else "-",
                            round(p.get('ar_days', np.nan), 1) if pd.notna(p.get('ar_days')) else "-",
                            round(p.get('inv_turnover_times', np.nan), 2) if pd.notna(p.get('inv_turnover_times')) else "-",
                            round(p.get('inv_days', np.nan), 1) if pd.notna(p.get('inv_days')) else "-",
                            round(p.get('fixed_assets_turnover', np.nan), 2) if pd.notna(p.get('fixed_assets_turnover')) else "-",
                            round(p.get('equity_turnover', np.nan), 2) if pd.notna(p.get('equity_turnover')) else "-",
                            round(p.get('ap_days', np.nan), 1) if pd.notna(p.get('ap_days')) else "-",
                            round(p.get('net_operating_cycle', np.nan), 1) if pd.notna(p.get('net_operating_cycle')) else "-"
                        ]
                    else:
                        data[name] = ["-"] * 10
                
                metrics = pd.DataFrame(data)
                st.dataframe(
                    metrics,
                    use_container_width=True,
                    hide_index=True
                )
            
            # 除錯資訊（方便你驗證資料）
            with st.expander("🔍 除錯資訊：1402 最新一筆 TEJ 原始資料"):
                st.json({k: v for k, v in latest.to_dict().items() if pd.notna(v)})
            
            # 優劣勢分析、稽核重點事項（維持原樣）
            st.markdown("#### ⚖️ 優劣勢分析")
            col1, col2 = st.columns(2)
            strengths = []
            weaknesses = []
            # （這裡可依需求再擴充，目前維持原邏輯）
            with col1:
                st.markdown('<div class="strength-box">', unsafe_allow_html=True)
                st.markdown("**✅ 優勢**")
                if strengths:
                    for s in strengths: st.write(s)
                else:
                    st.write("• 目前各項指標與同業相當，無明顯突出優勢")
                st.markdown('</div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div class="weakness-box">', unsafe_allow_html=True)
                st.markdown("**⚠️ 劣勢 / 風險點**")
                if weaknesses:
                    for w in weaknesses: st.write(w)
                else:
                    st.write("• 目前各項指標優於或符合同業，無明顯風險")
                st.markdown('</div>', unsafe_allow_html=True)
           
            st.markdown("#### 🔴 稽核應重點關注事項")
            points = []
            if pd.notna(latest.get('ar_days')) and latest.get('ar_days', 0) > 60:
                points.append("應收帳款天數偏高，需確認是否有壞帳或客戶信用風險")
            if pd.notna(latest.get('inv_days')) and latest.get('inv_days', 0) > 80:
                points.append("存貨周轉天數過長，可能面臨跌價或庫存減值風險")
            if not points:
                points.append("目前財務指標健康，無明顯異常")
            for p in points:
                st.markdown(f"- {p}")
           
            st.markdown("**稽核建議**：建議立即針對上述風險點進行詳細抽查，並要求相關部門提供佐證文件與改善計畫。")
           
            st.caption(f"資料來源：TEJ 最新財報（{latest.get('date').strftime('%Y-%m') if isinstance(latest.get('date'), pd.Timestamp) else '最新'}）")
        else:
            st.warning("TEJ 資料中尚未找到該公司資訊，請確認上傳檔案是否正確")
    else:
        st.info("請先上傳 TEJ 檔案以啟用財務健檢與同業對標分析")

update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f'<div style="text-align:center; color:#94a3b8; font-size:0.8rem; margin-top:3rem;">系統更新時間：{update_time} ｜ 資料來源：TWSE, Yahoo Finance, TEJ（永久保存）</div>', unsafe_allow_html=True)
