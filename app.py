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
# 這裡同步修改了瀏覽器分頁標題的 HQ -> Department
st.set_page_config(page_title="FENC Audit Department | Strategic Dashboard", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

# === 淺藍系現代化登入介面 ===
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True

    # 注入 Google 字體與全版 CSS
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
        .hero-title-solid {
            font-size: 80px;
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
        .login-label {
            font-size: 13px;
            color: #888888;
            margin-bottom: 8px;
            font-weight: 600;
        }
        
        div[data-baseweb="input"] > div {
            border: 1px solid #E0E0E0 !important;
            background-color: #ffffff !important;
            border-radius: 8px !important;
            height: 52px !important;
            box-shadow: none !important;
        }
        div[data-baseweb="input"] > div:hover { border-color: #1A1B20 !important; }
        div[data-baseweb="input"]:focus-within > div { border: 1.5px solid #1A1B20 !important; }
        
        div[data-baseweb="input"] input {
            color: #1A1B20 !important;
            padding: 12px 16px !important;
            font-size: 15px !important;
            font-weight: 500 !important;
        }
        
        .terms-text {
            font-size: 12px;
            color: #A0A0A0;
            margin: 20px 0;
            font-weight: 500;
        }
        .terms-text a { color: #A0A0A0; text-decoration: underline; }

        button[kind="primary"] {
            background-color: #1A1B20 !important;
            color: white !important;
            border-radius: 8px !important;
            height: 50px !important;
            font-weight: 600 !important;
            padding: 0 35px !important;
            border: none !important;
            letter-spacing: 0.5px;
        }
        button[kind="primary"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .it-contact {
            margin-top: 25px;
            text-align: center;
            font-size: 12.5px;
            color: #888888;
            font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)

    col_left, spacer, col_right = st.columns([1.1, 0.2, 0.9])
    
    with col_left:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div class="hero-subtitle">Strategic Command</div>', unsafe_allow_html=True)
        # 此處 HQ -> Department
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
        
        st.markdown('<div class="terms-text">By login, you agree to our <a href="#">Terms & Conditions</a></div>', unsafe_allow_html=True)
        
        btn_col, link_col = st.columns([1, 1])
        with btn_col:
            if st.button("Login Now ──", type="primary", use_container_width=True):
                if pwd == "AUDIT@01":
                    st.session_state["password_correct"] = True
                    st.rerun()
                elif pwd != "":
                    st.error("Invalid credentials")
        with link_col:
            st.markdown('<div style="text-align: right; padding-top: 15px;"><a href="#" style="color: #888; font-size: 13px; font-weight: 600; text-decoration: underline;">Forgot Passcode</a></div>', unsafe_allow_html=True)
        
        st.markdown('<div class="it-contact">IT Contact Curt Lee (#6855)</div>', unsafe_allow_html=True)

    return False

if not check_password():
    st.stop()

# === 以下為主儀表板程式碼 ===
st.markdown("""
    <style>
        .stApp { background: #000000 !important; color: #f5f5f7 !important; }
        .stApp::before { display: none !important; } 
        .main-title { font-size: 2.6rem; font-weight: 700; color: #f5f5f7; text-align: center; margin: 1.5rem 0; letter-spacing: 1px;}
        .sub-title { font-size: 1.15rem; color: #86868b; text-align: center; margin-bottom: 2.5rem; font-weight: 400;}
        /* ... 其他樣式保持不變 ... */
    </style>
""", unsafe_allow_html=True)

# 這裡也同步將主頁面的小標從 Headquarters 改為 Department 以維持一致性
st.markdown('<div class="main-title">Strategic Control Center</div><div class="sub-title">FENC Audit Department</div>', unsafe_allow_html=True)

# ... [其餘數據抓取與繪圖邏輯保持不變] ...
