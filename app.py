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

# ====================== TEJ 解析 ======================
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
if not check_password(): st.stop()

# === 2. 核心 UI 樣式（新增文青上傳區 CSS） ===
st.markdown("""
    <style>
        html, body, [class*="css"] { font-family: 'Noto Sans TC', 'Microsoft JhengHei', sans-serif !important; }
        .main-title { font-size: 2.2rem; font-weight: 800; color: #1e293b; text-align: center; margin: 1rem 0; letter-spacing: 1px;}
        .sub-title { font-size: 1rem; color: #64748b; text-align: center; margin-bottom: 2rem; font-weight: 500;}
        .ai-score-box { background: linear-gradient(135deg, #1e293b, #0f172a); color: white; padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.15);}
        .strength-box { background: #ffffff; border-left: 5px solid #22c55e; padding: 15px; border-radius: 8px; margin-top:15px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);}
        .weakness-box { background: #ffffff; border-left: 5px solid #ef4444; padding: 15px; border-radius: 8px; margin-top:15px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);}
        
        /* 文青上傳區樣式 */
        .stFileUploader > div > div {
            background: #f8f1e9 !important;
            border: 2px dashed #d1b48c !important;
            border-radius: 16px !important;
            padding: 40px 20px !important;
            text-align: center !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03) !important;
        }
        .stFileUploader label {
            color: #8c6f4e !important;
            font-size: 1.1rem !important;
            font-weight: 500 !important;
            letter-spacing: 0.5px !important;
        }
    </style>
""", unsafe_allow_html=True)
st.markdown('<div class="main-title">遠東集團 (Far Eastern Group)</div><div class="sub-title">聯合稽核總部 ｜ 戰略決策儀表板</div>', unsafe_allow_html=True)

# === 3. API 與真實資料抓取模組（保持不變）===
# （以下省略與之前完全相同的 API 函數、plot 函數、MACRO_IMPACT、market_categories）

# === 5. 左側選單（已改成文青風） ===
market_categories = { ... }  # 與之前完全相同

with st.sidebar:
    st.header("🎯 戰略監控目標")
    st.subheader("📤 數據庫資料匯入")
    st.caption("請上傳三個 TEJ 檔案 — 上傳一次後永久保存")
    
    uploaded_files = st.file_uploader(
        "檔案上傳路徑",
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
                    st.success("✅ TEJ 資料已成功上傳並永久保存")
    else:
        if 'tej_data' not in st.session_state:
            saved = load_saved_tej_data()
            if saved is not None:
                st.session_state['tej_data'] = saved
                st.success("✅ 已自動載入永久保存的 TEJ 資料")
    
    if st.button("🗑️ 清除永久保存的 TEJ 資料"):
        if clear_saved_tej_data():
            st.session_state.pop('tej_data', None)
            st.success("已清除")
            st.rerun()
    
    st.markdown("---")
    selected_category = st.selectbox("板塊分類", list(market_categories.keys()))
    st.markdown("---")
    options_dict = market_categories[selected_category]
    option = st.radio("監控標的", list(options_dict.keys()))
    code = options_dict[option]
    is_tw_stock = code.isdigit()

# === 其餘程式碼（價格顯示、圖表、下半部分析）與之前版本完全相同 ===
# （為避免過長，這裡省略，但實際上請保留你原本的價格顯示、圖表、下半部 TEJ 分析部分）

update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f'<div style="text-align:center; color:#94a3b8; font-size:0.8rem; margin-top:3rem;">系統更新時間：{update_time} ｜ 資料來源：TWSE, Yahoo Finance, TEJ（永久保存）</div>', unsafe_allow_html=True)
