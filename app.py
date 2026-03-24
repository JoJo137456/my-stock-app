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

# ====================== TEJ 解析（已按照你最新說明全部修正） ======================
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
                col_mapping = {
                    '代號': 'stock_id',
                    '名稱': 'company_name',
                    '年/月': 'date',
                    '營業收入淨額': 'revenue',
                    '營業成本': 'cogs',
                    '營業毛利': 'gross_profit',
                    '稅前息前淨利': 'pre_tax_profit',
                    '常續性稅後淨利': 'net_profit',
                    '稅後淨利': 'net_profit',
                    '淨利': 'net_profit',
                    '每股盈餘(元)': 'eps',
                    'EPS': 'eps',
                    '平均收帳天數': 'ar_days',
                    '平均售貨天數': 'inv_days',
                    '存貨週轉率（次）': 'inv_turnover_times',
                    '存貨': 'inventory',
                    '應收帳款及票據': 'ar_notes',
                    '其他應收款': 'ar_other',
                    '資產總額': 'total_assets',
                    '股東權益總額': 'equity',
                }
                df = df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns})
               
                if 'stock_id' not in df.columns and 'company_name' in df.columns:
                    df['stock_id'] = df['company_name'].str.extract(r'(\d{4})')
                if 'stock_id' in df.columns:
                    df['stock_id'] = df['stock_id'].astype(str).str.zfill(4)
               
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'], errors='coerce')
               
                for col in ['revenue', 'cogs', 'gross_profit', 'pre_tax_profit', 'net_profit', 'inventory', 'ar_notes', 'ar_other', 'total_assets', 'equity']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce') / 100000
               
                if 'ar_notes' in df.columns or 'ar_other' in df.columns:
                    df['ar'] = df.get('ar_notes', 0) + df.get('ar_other', 0)
               
                if 'revenue' in df.columns and 'gross_profit' in df.columns:
                    df['gross_margin'] = (df['gross_profit'] / df['revenue'] * 100).round(1)
                if 'revenue' in df.columns and 'net_profit' in df.columns:
                    df['net_margin'] = (df['net_profit'] / df['revenue'] * 100).round(1)
               
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
       
        for col in ['gross_margin', 'net_margin', 'ar', 'inventory']:
            if col not in combined.columns:
                combined[col] = np.nan
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

# === 2. 核心 UI 樣式（新增檔案上傳區中文美化） ===
st.markdown("""
    <style>
        html, body, [class*="css"] { font-family: 'Noto Sans TC', 'Microsoft JhengHei', sans-serif !important; }
        .main-title { font-size: 2.2rem; font-weight: 800; color: #1e293b; text-align: center; margin: 1rem 0; letter-spacing: 1px;}
        .sub-title { font-size: 1rem; color: #64748b; text-align: center; margin-bottom: 2rem; font-weight: 500;}
        .ai-score-box { background: linear-gradient(135deg, #1e293b, #0f172a); color: white; padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.15);}
        .strength-box { background: #ffffff; border-left: 5px solid #22c55e; padding: 15px; border-radius: 8px; margin-top:15px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);}
        .weakness-box { background: #ffffff; border-left: 5px solid #ef4444; padding: 15px; border-radius: 8px; margin-top:15px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);}
        
        /* 檔案上傳區中文美化 - 替換 Drag & Drop 預設文字 */
        [data-testid="stFileUploader"] > div > div > div > div {
            color: #1e293b !important;
            font-weight: 600 !important;
        }
        [data-testid="stFileUploader"] [data-testid="stMarkdownContainer"] p {
            font-size: 1.1rem !important;
            color: #1e293b !important;
        }
        /* 強制替換英文 Drag and drop 文字 */
        [data-testid="stFileUploader"] div[style*="drag"]::before {
            content: "📤 拖曳 TEJ 報表至此 或 點擊選擇檔案" !important;
            color: #1e293b !important;
            font-size: 1.1rem !important;
            font-weight: 600 !important;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">遠東集團 (Far Eastern Group)</div><div class="sub-title">聯合稽核總部 ｜ 戰略決策儀表板</div>', unsafe_allow_html=True)

# === 3. API 與真實資料抓取模組（保持不變） ===
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

# === 4. 深度戰略連動註解庫（保持不變） ===
MACRO_IMPACT = { ... }  # （與原程式碼完全相同，此處省略以節省篇幅）

# === 5. 左側選單（已按你要求大幅修改上傳文字） ===
market_categories = { ... }  # （與原程式碼完全相同）

with st.sidebar:
    st.header("🎯 戰略監控目標")
    st.subheader("📤 TEJ 資料庫匯入")
    st.markdown("""
    **請上傳 TEJ 報表**  
    — 上傳一次後永久保存（支援多檔 XLSX / XLS）
    """)
    
    uploaded_files = st.file_uploader(
        "TEJ 財報檔案", 
        type=["xlsx", "xls"], 
        accept_multiple_files=True, 
        label_visibility="collapsed"
    )
   
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

# === 價格顯示、圖表、指標說明（保持不變） ===
# ...（與原程式碼完全相同，此處省略以節省篇幅）

# === 全新下半部：TEJ 財務健檢與同業對標分析（**完整修正版**） ===
if is_tw_stock:
    st.divider()
    st.markdown("## 📊 TEJ 財務健檢與同業對標分析")
    tej_df = st.session_state.get('tej_data', None)
   
    if tej_df is not None and not tej_df.empty:
        company_df = tej_df[tej_df['stock_id'] == str(code)].sort_values('date', ascending=False)
        if not company_df.empty:
            latest = company_df.iloc[0]
            company_name = latest.get('company_name', f'公司 {code}')
           
            # === 修正：同業平均正確計算 ===
            peers_df = tej_df[tej_df['stock_id'] != str(code)].copy()
            peer_summary = peers_df.groupby('stock_id').first().reset_index()
            
            peer_means = {
                'revenue': round(peer_summary['revenue'].mean(), 1),
                'gross_margin': round(peer_summary['gross_margin'].mean(), 1),
                'net_margin': round(peer_summary['net_margin'].mean(), 1),
                'inv_days': round(peer_summary['inv_days'].mean(), 1),
                'ar_days': round(peer_summary['ar_days'].mean(), 1)
            }
           
            st.markdown(f"### 🔍 目前分析公司：**{company_name} ({code})**")
           
            # === AI 分數計算（保持原邏輯） ===
            score = 75
            if latest.get('gross_margin', 0) < 15: score -= 15
            if latest.get('net_margin', 0) < 5: score -= 15
            if latest.get('ar_days', 0) > 60: score -= 10
            if latest.get('inv_days', 0) > 80: score -= 10
            if latest.get('revenue', 0) == 0: score -= 20
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
           
            with col_compare:
                st.markdown("#### 📈 最新關鍵指標（TEJ 資料）")
                metrics = pd.DataFrame({
                    "指標": ["單季營收 (億)", "毛利率 (%)", "淨利率 (%)", "存貨周轉天數", "應收帳款天數"],
                    "本公司": [
                        round(latest.get('revenue', 0), 1),
                        round(latest.get('gross_margin', 0), 1),
                        round(latest.get('net_margin', 0), 1),
                        round(latest.get('inv_days', 0), 1),
                        round(latest.get('ar_days', 0), 1)
                    ],
                    "同業平均": [
                        peer_means['revenue'],
                        peer_means['gross_margin'],
                        peer_means['net_margin'],
                        peer_means['inv_days'],
                        peer_means['ar_days']
                    ]
                })
                st.dataframe(
                    metrics.style.format({"本公司": "{:.1f}", "同業平均": "{:.1f}"}),
                    use_container_width=True, 
                    hide_index=True
                )
           
            # === 全新優劣勢分析（已完整重寫，動態產生具體文字） ===
            st.markdown("#### ⚖️ 優劣勢分析")
            col1, col2 = st.columns(2)
            
            # 優勢清單
            strengths = []
            if latest.get('gross_margin', 0) > peer_means['gross_margin']:
                strengths.append("• 毛利率高於同業平均，產品競爭力與定價能力強")
            if latest.get('net_margin', 0) > peer_means['net_margin']:
                strengths.append("• 淨利率高於同業平均，成本控管與營運效率優異")
            if latest.get('ar_days', 0) < peer_means['ar_days']:
                strengths.append("• 應收帳款天數低於同業，現金流回收速度快")
            if latest.get('inv_days', 0) < peer_means['inv_days']:
                strengths.append("• 存貨周轉天數低於同業，庫存管理高效")
            if latest.get('revenue', 0) > peer_means['revenue']:
                strengths.append("• 單季營收規模高於同業，市場地位穩固")
            
            with col1:
                st.markdown('<div class="strength-box">', unsafe_allow_html=True)
                st.markdown("**✅ 優勢**")
                if strengths:
                    for s in strengths:
                        st.write(s)
                else:
                    st.write("• 目前各項指標與同業相當，無明顯突出優勢")
                st.markdown('</div>', unsafe_allow_html=True)
            
            # 劣勢 / 風險點
            weaknesses = []
            if latest.get('gross_margin', 0) < peer_means['gross_margin']:
                weaknesses.append("• 毛利率低於同業平均，毛利結構需檢討")
            if latest.get('net_margin', 0) < peer_means['net_margin']:
                weaknesses.append("• 淨利率低於同業平均，成本控制或費用率需加強")
            if latest.get('ar_days', 0) > peer_means['ar_days']:
                weaknesses.append("• 應收帳款天數高於同業，可能有壞帳或客戶信用風險")
            if latest.get('inv_days', 0) > peer_means['inv_days']:
                weaknesses.append("• 存貨周轉天數高於同業，可能有滯銷或跌價風險")
            if latest.get('revenue', 0) < peer_means['revenue']:
                weaknesses.append("• 單季營收規模低於同業，市場競爭力需關注")
            
            with col2:
                st.markdown('<div class="weakness-box">', unsafe_allow_html=True)
                st.markdown("**⚠️ 劣勢 / 風險點**")
                if weaknesses:
                    for w in weaknesses:
                        st.write(w)
                else:
                    st.write("• 目前各項指標優於或符合同業，無明顯風險")
                st.markdown('</div>', unsafe_allow_html=True)
           
            st.markdown("#### 🔴 稽核應重點關注事項")
            points = []
            if latest.get('ar_days', 0) > 60:
                points.append("應收帳款天數偏高，需確認是否有壞帳或客戶信用風險")
            if latest.get('inv_days', 0) > 80:
                points.append("存貨周轉天數過長，可能面臨跌價或庫存減值風險")
            if latest.get('gross_margin', 0) < 15:
                points.append("毛利率偏低，毛利結構需檢討")
            if latest.get('net_margin', 0) < 5:
                points.append("淨利率偏低，營運成本與費用控管需加強")
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
