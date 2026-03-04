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
# 同步更新分頁標題
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
        
        .stApp {
            background-color: #F0F8FF !important; 
            font-family: 'Poppins', 'Noto Sans TC', sans-serif !important;
        }
        
        .stApp::before {
            content: '';
            position: fixed;
            bottom: -30vh;
            left: -15vw;
            width: 65vw;
            height: 65vw;
            background-color: #D6EAF8; 
            border-radius: 50%;
            z-index: 0;
        }

        .main .block-container {
            z-index: 1;
            padding-top: 10vh !important;
        }

        .hero-subtitle {
            font-size: 16px;
            font-weight: 700;
            color: #1A1B20;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            letter-spacing: 0.5px;
        }
        .hero-subtitle::before {
            content: '';
            display: inline-block;
            width: 40px;
            height: 2px;
            background-color: #1A1B20;
            margin-right: 15px;
        }
        
        /* 修正處：微調字體大小以適應較長的單字 */
        .hero-title-solid {
            font-size: 70px; 
            font-weight: 800;
            color: #1A1B20;
            line-height: 1.1;
            margin-bottom: 0;
            letter-spacing: -2px;
        }
        
        .hero-title-outline {
            font-size: 55px; 
            font-weight: 900;
            color: transparent;
            -webkit-text-stroke: 1.5px #1A1B20;
            line-height: 1.2;
            margin-top: 5px;
            margin-bottom: 50px;
            letter-spacing: 1px;
        }
        
        .label-dashboard {
            background-color: #1A1B20;
            color: #ffffff;
            padding: 14px 32px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            display: inline-block;
            cursor: default; 
            letter-spacing: 1px;
        }

        [data-testid="column"]:nth-of-type(3) {
            background: #ffffff;
            border-radius: 20px;
            padding: 40px 35px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.04);
            margin-top: 20px;
        }
        
        .login-dept {
            font-size: 28px;
            color: #1A1B20;
            font-weight: 900;
            margin-bottom: 2px;
            letter-spacing: 1.5px;
        }
        .login-title {
            font-size: 16px;
            font-weight: 600;
            color: #888888;
            margin-bottom: 30px;
        }
        
        /* ... 其餘 CSS 保持不變 ... */
        .login-label { font-size: 13px; color: #888888; margin-bottom: 8px; font-weight: 600; }
        div[data-baseweb="input"] > div { border: 1px solid #E0E0E0 !important; background-color: #ffffff !important; border-radius: 8px !important; height: 52px !important; }
        div[data-baseweb="input"] input { color: #1A1B20 !important; padding: 12px 16px !important; font-size: 15px !important; }
        button[kind="primary"] { background-color: #1A1B20 !important; color: white !important; border-radius: 8px !important; height: 50px !important; font-weight: 600 !important; }
    </style>
    """, unsafe_allow_html=True)

    col_left, spacer, col_right = st.columns([1.1, 0.2, 0.9])
    
    with col_left:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div class="hero-subtitle">Strategic Command</div>', unsafe_allow_html=True)
        # 關鍵修正處：將 HQ 改為 Department
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

if not check_password():
    st.stop()

# === 主儀表板內容 (Header 部分同步更新) ===
st.markdown("""
    <style>
        .stApp { background: #000000 !important; color: #f5f5f7 !important; }
        .main-title { font-size: 2.6rem; font-weight: 700; color: #f5f5f7; text-align: center; margin-top: 1.5rem; }
        .sub-title { font-size: 1.15rem; color: #86868b; text-align: center; margin-bottom: 2.5rem; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">Strategic Control Center</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">FENC Audit Department</div>', unsafe_allow_html=True)

# ... 其餘邏輯代碼 ...
