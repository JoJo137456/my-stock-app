import streamlit as st
import twstock
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, time as dt_time
import pytz
import requests
import urllib3
import yfinance as yf

# === 0. System Level Fixes ===
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
original_request = requests.Session.request
def patched_request(self, method, url, *args, **kwargs):
    kwargs['verify'] = False
    return original_request(self, method, url, *args, **kwargs)
requests.Session.request = patched_request

# === 1. Dashboard Initialization ===
st.set_page_config(page_title="FENC Audit HQ | Strategic Dashboard", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

# === 更現代的中英文字體 + 登入頁面優化 ===
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True

    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Noto+Sans+TC:wght@400;500;700;900&display=swap');

        /* 全局字體與背景 */
        .stApp {
            background-color: #F8FAFC !important;
            font-family: 'Inter', 'Noto Sans TC', system-ui, sans-serif !important;
        }

        /* 隱藏不必要的元素 */
        [data-testid="stSidebar"], header, [data-testid="collapsedControl"] {display: none !important;}

        /* 大圓形裝飾 */
        .stApp::before {
            content: '';
            position: fixed;
            bottom: -35vh;
            left: -20vw;
            width: 80vw;
            height: 80vw;
            background: radial-gradient(circle at 30% 70%, #E0F2FE 0%, #DBEAFE 40%, transparent 70%);
            border-radius: 50%;
            z-index: 0;
            opacity: 0.7;
        }

        .main .block-container {
            z-index: 2;
            padding-top: 8vh !important;
        }

        /* 左側標題區 */
        .hero-subtitle {
            font-family: 'Inter', sans-serif;
            font-size: 1.1rem;
            font-weight: 700;
            color: #0F172A;
            letter-spacing: 1.8px;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
        }
        .hero-subtitle::before {
            content: '';
            width: 48px;
            height: 3px;
            background: #0F172A;
            margin-right: 1.2rem;
            border-radius: 2px;
        }

        .hero-title-solid {
            font-family: 'Inter', 'Noto Sans TC', sans-serif;
            font-size: 5.8rem;
            font-weight: 900;
            color: #0F172A;
            line-height: 0.95;
            letter-spacing: -3.5px;
            margin: 0;
        }

        .hero-title-outline {
            font-family: 'Inter', 'Noto Sans TC', sans-serif;
            font-size: 3.8rem;
            font-weight: 900;
            color: transparent;
            -webkit-text-stroke: 1.8px #0F172A;
            -webkit-text-fill-color: transparent;
            line-height: 1;
            letter-spacing: -1.2px;
            margin: 0.4rem 0 3rem 0;
        }

        .label-dashboard {
            background: #0F172A;
            color: white;
            font-family: 'Inter', sans-serif;
            font-weight: 700;
            font-size: 0.95rem;
            padding: 0.8rem 2.2rem;
            border-radius: 10px;
            letter-spacing: 1.5px;
            display: inline-block;
        }

        /* 右側登入卡片 */
        [data-testid="column"]:nth-of-type(3) {
            background: white;
            border-radius: 24px;
            padding: 3.2rem 2.8rem;
            box-shadow: 0 20px 40px rgba(0,0,0,0.06);
            margin-top: 1.5rem;
            border: 1px solid #E2E8F0;
        }

        .login-dept {
            font-family: 'Noto Sans TC', sans-serif;
            font-size: 2.1rem;
            font-weight: 900;
            color: #0F172A;
            letter-spacing: 0.8px;
            margin-bottom: 0.3rem;
        }

        .login-title {
            font-family: 'Inter', sans-serif;
            font-size: 1.1rem;
            font-weight: 500;
            color: #64748B;
            margin-bottom: 2.2rem;
        }

        .login-label {
            font-family: 'Inter', sans-serif;
            font-size: 0.9rem;
            font-weight: 600;
            color: #64748B;
            margin-bottom: 0.5rem;
        }

        /* 輸入框美化 */
        div[data-baseweb="input"] > div {
            border: 1px solid #CBD5E1 !important;
            border-radius: 10px !important;
            background: white !important;
            height: 54px !important;
        }
        div[data-baseweb="input"] input {
            font-family: 'Inter', monospace;
            font-size: 1.05rem;
            font-weight: 500;
            letter-spacing: 0.5px;
            color: #0F172A !important;
        }
        div[data-baseweb="input"]:focus-within > div {
            border-color: #0F172A !important;
            box-shadow: 0 0 0 3px rgba(15,23,42,0.12) !important;
        }

        /* 按鈕 */
        button[kind="primary"] {
            background: #0F172A !important;
            color: white !important;
            border-radius: 10px !important;
            height: 54px !important;
            font-family: 'Inter', sans-serif;
            font-weight: 700 !important;
            font-size: 1.05rem !important;
            letter-spacing: 0.8px;
        }
        button[kind="primary"]:hover {
            background: #1E293B !important;
            transform: translateY(-1px);
            box-shadow: 0 8px 24px rgba(15,23,42,0.18) !important;
        }

        .terms-text, .it-contact {
            font-family: 'Inter', sans-serif;
            color: #64748B;
            font-size: 0.82rem;
            font-weight: 500;
        }
    </style>
    """, unsafe_allow_html=True)

    col_left, spacer, col_right = st.columns([1.1, 0.15, 0.95])

    with col_left:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown('<div class="hero-subtitle">STRATEGIC COMMAND</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-title-solid">AUDIT HQ</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-title-outline">遠東集團</div>', unsafe_allow_html=True)
        st.markdown('<div class="label-dashboard">INTELLIGENCE NEXUS</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="login-dept">遠東聯合稽核總部</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-title">請輸入通行碼</div>', unsafe_allow_html=True)

        st.markdown('<div class="login-label">帳號 / Customer ID</div>', unsafe_allow_html=True)
        st.text_input("", value="fenc07822", label_visibility="collapsed", key="acc_id")

        st.markdown('<div class="login-label" style="margin-top:1.4rem;">通行碼 / Passcode</div>', unsafe_allow_html=True)
        pwd = st.text_input("", type="password", label_visibility="collapsed", key="pwd")

        st.markdown('<div class="terms-text" style="margin:1.8rem 0;">登入即表示同意<a href="#" style="color:#64748B;"> 使用條款</a></div>', unsafe_allow_html=True)

        btn_col, link_col = st.columns([1, 1])
        with btn_col:
            if st.button("登入系統 ──", type="primary", use_container_width=True):
                if pwd == "AUDIT@01":
                    st.session_state["password_correct"] = True
                    st.rerun()
                elif pwd != "":
                    st.error("通行碼錯誤")
        with link_col:
            st.markdown('<div style="text-align:right; padding-top:1.1rem;"><a href="#" style="color:#64748B; font-size:0.9rem; font-weight:600; text-decoration:underline;">忘記通行碼？</a></div>', unsafe_allow_html=True)

        st.markdown('<div class="it-contact" style="margin-top:2rem; text-align:center;">IT 聯絡：Curt Lee (#6855)</div>', unsafe_allow_html=True)

    return False

if not check_password():
    st.stop()

# ────────────────────────────────────────────────
#                  主儀表板開始
# ────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Noto+Sans+TC:wght@500;700;900&display=swap');

    .stApp {
        background: #0F172A !important;
        color: #E2E8F0 !important;
        font-family: 'Inter', 'Noto Sans TC', sans-serif !important;
    }

    .stApp::before { display: none !important; }

    .main-title {
        font-family: 'Inter', sans-serif;
        font-size: 2.8rem;
        font-weight: 800;
        color: #F1F5F9;
        text-align: center;
        letter-spacing: -0.8px;
        margin: 1.8rem 0 0.6rem;
    }

    .sub-title {
        font-family: 'Inter', sans-serif;
        font-size: 1.18rem;
        font-weight: 400;
        color: #94A3B8;
        text-align: center;
        margin-bottom: 2.4rem;
    }

    .chart-container {
        background: #1E293B;
        padding: 1.8rem;
        border-radius: 16px;
        border: 1px solid #334155;
        margin-bottom: 1.6rem;
    }

    div[data-testid="metric-container"] {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.2rem;
    }
    div[data-testid="metric-container"] > div {
        color: #F1F5F9 !important;
        font-family: 'Inter', monospace !important;
        font-variant-numeric: tabular-nums;
    }
    div[data-testid="metric-container"] label {
        color: #94A3B8 !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        letter-spacing: 0.6px;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">策略指揮中心</div><div class="sub-title">遠東聯合稽核總部 • Strategic Control Center</div>', unsafe_allow_html=True)

# 以下維持原有的函數與邏輯不變，只替換顯示用的中英文標籤與風格
# （這裡省略中間大量不變的函數與邏輯，只展示關鍵顯示部分改動）

# ... （中間所有函數保持原樣：check_market_status, fetch_twse_history_proxy, ... 等）

# 在顯示價格區塊可考慮加上 font-variant-numeric: tabular-nums; 讓數字對齊更好看
# 但因為已經在 .metric-container 裡面設定了 monospace + tabular-nums，所以整體數字會更整齊

# 最後的價格顯示區塊可微調文字（可選）
st.markdown(f"""
<div style="background-color: #1E293B; padding: 2.2rem 2rem; border-radius: 16px; margin: 1.5rem 0; border: 1px solid #334155;">
    <div style="font-family:'Inter',sans-serif; font-size:1.15rem; font-weight:600; color:#94A3B8; margin-bottom:0.6rem;">{option}</div>
    <div style="display:flex; align-items:baseline; gap:1.4rem;">
        <span style="font-family:'Inter',monospace; font-size:4.2rem; font-weight:800; color:#F1F5F9; letter-spacing:-1px;">
            {currency_symbol} {current_price:,.2f}
        </span>
        <span style="font-family:'Inter',sans-serif; font-size:2rem; font-weight:700; color:{font_color};">
            {change:+.2f}　({pct:+.2f}%)
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# 圖表區塊標題可再加強一點層次感（可選）
with col1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    if df_intra is not None and not df_intra.empty:
        fig = plot_intraday_line(df_intra)
        if fig:
            fig.update_layout(title_text=f"盤中即時走勢（{interval_str}）")
            st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    if not df_daily.empty:
        fig = plot_daily_k(df_daily)
        if fig:
            fig.update_layout(title_text="近六個月K線走勢")
            st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
