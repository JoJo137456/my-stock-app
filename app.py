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

# === 登入介面（維持原樣）===
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True
    st.markdown("""<style>@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;800&family=Noto+Sans+TC:wght@300;400;500;700;800&display=swap');
        [data-testid="stSidebar"], header, [data-testid="collapsedControl"] {display: none !important;}
        .stApp { background-color: #F0F8FF !important; font-family: 'Poppins', 'Noto Sans TC', sans-serif !important; }
        .hero-title-solid { font-size: 70px; font-weight: 800; color: #1A1A20; line-height: 1.1; margin-bottom: 0; letter-spacing: -2px; }
        .hero-title-outline { font-size: 55px; font-weight: 900; color: transparent; -webkit-text-stroke: 1.5px #1A1A20; line-height: 1.2; margin-top: 5px; margin-bottom: 50px; }
        .label-dashboard { background-color: #1A1B20; color: #ffffff; padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 14px; display: inline-block; }
    </style>""", unsafe_allow_html=True)
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

# === 2. 核心 UI 樣式（新增報酬率卡片與定義卡片樣式）===
st.markdown("""
<style>
    html, body, [class*="css"] { font-family: 'Noto Sans TC', 'Microsoft JhengHei', sans-serif !important; }
    .main-title { font-size: 2.2rem; font-weight: 800; color: #1e293b; text-align: center; margin: 1rem 0; letter-spacing: 1px;}
    .sub-title { font-size: 1rem; color: #64748b; text-align: center; margin-bottom: 2rem; font-weight: 500;}
    .returns-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(168px, 1fr)); gap: 16px; margin: 24px 0 32px 0; }
    .return-card { background: #ffffff; padding: 22px 18px; border-radius: 14px; text-align: center; box-shadow: 0 6px 16px rgba(0,0,0,0.04); border: 1px solid #f1f5f9; transition: all 0.2s cubic-bezier(0.4,0,0.2,1); }
    .return-card:hover { transform: translateY(-4px); box-shadow: 0 12px 24px rgba(0,0,0,0.08); }
    .return-label { font-size: 13.5px; color: #64748b; font-weight: 600; letter-spacing: 0.6px; margin-bottom: 8px; }
    .return-value { font-size: 27px; font-weight: 800; line-height: 1.05; }
    .definition-box { background: #ffffff; padding: 28px 32px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 6px 20px rgba(0,0,0,0.035); margin-bottom: 32px; }
    .definition-text { font-size: 15.8px; line-height: 1.85; color: #334155; padding-left: 22px; border-left: 4px solid #3b82f6; font-weight: 500; }
</style>
""", unsafe_allow_html=True)
st.markdown('<div class="main-title">遠東集團 (Far Eastern Group)</div><div class="sub-title">聯合稽核總部 ｜ 戰略決策儀表板</div>', unsafe_allow_html=True)

# === 3~5. 資料抓取、財務計算、繪圖模組（與之前相同，僅 fetch 擴展 1 年）===
# （省略與前版完全相同的 fetch_twse_history_proxy、fetch_us_history、get_intraday_chart_data、get_resilient_financials、calculate_ai_audit_score、MACRO_IMPACT、INDUSTRY_PEERS、TARGET_DEFINITIONS、fetch_peers_ccc_real、plot_daily_k、plot_intraday_line、calculate_period_returns 函式）
# 請直接複製前版程式碼中這些部分（已確認無變動）

# === 6. 左側選單與即時資料 ===
market_categories = { ... }  # 與前版完全相同
with st.sidebar:
    # 與前版相同

# === 即時股價顯示 ===
# ...（與前版相同，取得 current_price、change、pct）

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

# === 新設計：標的定義卡片（緊接股價後面，無標題文字）===
if option in TARGET_DEFINITIONS:
    exp_text = TARGET_DEFINITIONS[option]
    st.markdown(f"""
    <div class="definition-box">
        <div class="definition-text">{exp_text}</div>
    </div>
    """, unsafe_allow_html=True)

# === 新設計：多期間報酬率（現代卡片風格）===
period_returns = calculate_period_returns(df_daily, current_price)
if period_returns:
    st.markdown("### 📅 多期間報酬率指標 (Multi-Period Returns)")
    
    return_html = '<div class="returns-grid">'
    for label, ret in period_returns.items():
        if ret == "N/A":
            disp_val = "N/A"
            color = "#94a3b8"
        else:
            disp_val = f"{ret:+.2f}%"
            color = "#ef4444" if ret >= 0 else "#22c55e"
        return_html += f'''
        <div class="return-card">
            <div class="return-label">{label}</div>
            <div class="return-value" style="color:{color};">{disp_val}</div>
        </div>
        '''
    return_html += '</div>'
    st.markdown(return_html, unsafe_allow_html=True)

# === 警示判斷區塊（維持專業整齊）===
st.markdown("### ⚠️ 報酬率警示判斷與判斷標準")
# （後續警示標準與觸發警示區塊與前版完全相同）

# === 圖表與財務戰情室（維持原樣）===
col1, col2 = st.columns([1, 1])
with col1:
    if df_intra is not None and not df_intra.empty: st.plotly_chart(plot_intraday_line(df_intra), use_container_width=True)
with col2:
    if not df_daily.empty: st.plotly_chart(plot_daily_k(df_daily), use_container_width=True)

# 下半部財務戰情室（與前版相同）

update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f'<div style="text-align:center; color:#94a3b8; font-size:0.8rem; margin-top:3rem;">系統更新時間：{update_time} ｜ 資料來源：TWSE, Yahoo Finance, FinMind</div>', unsafe_allow_html=True)
