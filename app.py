import streamlit as st
import twstock
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, time as dt_time
import pytz
import requests
import urllib3
import yfinance as yf
import base64
import os

# === 0. System Fix ===
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
original_request = requests.Session.request
def patched_request(self, method, url, *args, **kwargs):
    kwargs['verify'] = False
    return original_request(self, method, url, *args, **kwargs)
requests.Session.request = patched_request

# === 1. Page Config ===
st.set_page_config(page_title="FENC Audit HQ | Strategic Dashboard", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

# ================================
# 🔐 SCADA LOGIN SYSTEM
# ================================
def check_password():

    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    # === 背景圖 ===
    if os.path.exists('bg.jpg'):
        with open('bg.jpg', 'rb') as f:
            encoded_bg = base64.b64encode(f.read()).decode()
        st.markdown(f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded_bg}") !important;
            background-size: cover !important;
            background-position: center !important;
            background-attachment: fixed !important;
        }}
        .stApp::before {{
            content: '';
            position: fixed;
            inset: 0;
            background: linear-gradient(rgba(0,0,0,0.8), rgba(0,0,0,0.9));
            z-index: -1;
        }}
        </style>
        """, unsafe_allow_html=True)

    # === SCADA CSS 強化最終版 ===
    st.markdown("""
    <style>
    [data-testid="stSidebar"], header, [data-testid="collapsedControl"] {display:none !important;}

    .scada-card {
        background: rgba(10,14,20,0.92);
        backdrop-filter: blur(25px);
        border: 2px solid #00ff9f;
        border-radius: 18px;
        padding: 60px 55px 50px;
        max-width: 460px;
        margin: 90px auto 40px;
        box-shadow:
            0 0 40px rgba(0,255,159,0.35),
            0 0 80px rgba(0,255,159,0.15),
            0 30px 60px rgba(0,0,0,0.85);
    }

    .scada-title {
        font-size: 42px;
        font-weight: 900;
        color: #ffffff;
        text-align: center;
        letter-spacing: 3px;
        margin-bottom: 8px;
        text-shadow:
            0 0 10px #00ff9f,
            0 0 20px #00ff9f,
            0 0 40px #00ff9f,
            0 0 80px #00ff9f;
    }

    .scada-subtitle {
        font-size: 17px;
        color: #a0f0d0;
        text-align: center;
        margin-bottom: 50px;
        font-weight: 500;
        text-shadow: 0 0 15px #00ff9f;
    }

    .scada-label {
        font-size: 14px;
        font-weight: 800;
        color: #00ff9f;
        margin: 28px 0 10px 0;
        letter-spacing: 2px;
        text-transform: uppercase;
        display: block;
        text-align: center;
        text-shadow:
            0 0 8px #00ff9f,
            0 0 18px #00ff9f,
            0 0 35px #00ff9f;
    }

    .scada-org-text {
        color: #ffffff;
        font-size: 18px;
        font-weight: 600;
        text-align: center;
        letter-spacing: 1px;
        margin-bottom: 25px;
        text-shadow: 0 0 8px rgba(255,255,255,0.6);
    }

    div[data-baseweb="input"] > div {
        background-color: transparent !important;
        border: none !important;
        border-bottom: 1px solid rgba(0,255,159,0.3) !important;
        border-radius: 0 !important;
        height: 45px !important;
        box-shadow: none !important;
        padding: 0 !important;
    }

    div[data-baseweb="input"] input {
        color: #ffffff !important;
        text-align: center !important;
        font-size: 20px !important;
        font-weight: 500 !important;
        padding: 0 !important;
        margin: 0 !important;
        letter-spacing: 1.5px;
        background: transparent !important;
    }

    div[data-baseweb="input"] > div > div:nth-child(2) {
        display: none !important;
    }

    div[data-baseweb="input"]:focus-within > div {
        border-bottom: 2px solid #00ff9f !important;
        box-shadow:
            0 10px 20px -10px rgba(0,255,159,0.9),
            0 0 25px rgba(0,255,159,0.7);
    }

    button[kind="primary"] {
        background: linear-gradient(90deg,#00b8ff,#0090ff) !important;
        color:#fff !important;
        font-size:18px !important;
        font-weight:700 !important;
        height:60px !important;
        border-radius:12px !important;
        margin-top:35px;
        letter-spacing:1.5px;
        box-shadow:0 0 25px rgba(0,184,255,0.5);
    }

    button[kind="primary"]:hover {
        background: linear-gradient(90deg,#00ff9f,#00b8ff) !important;
        box-shadow:
            0 0 30px rgba(0,255,159,0.9),
            0 0 60px rgba(0,255,159,0.6);
        transform: scale(1.03);
    }

    .scada-footer {
        text-align:center;
        margin-top:45px;
        font-size:15px;
    }

    .scada-footer a, .scada-footer span {
        color:#00ff9f;
        font-weight:700;
        letter-spacing:0.5px;
        text-shadow:
            0 0 8px #00ff9f,
            0 0 18px #00ff9f,
            0 0 35px #00ff9f;
    }

    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,1.6,1])
    with col2:
        st.markdown('<div class="scada-card">', unsafe_allow_html=True)
        st.markdown('<div class="scada-title">AUDIT HQ</div>', unsafe_allow_html=True)
        st.markdown('<div class="scada-subtitle">FENC Corporate Control Access</div>', unsafe_allow_html=True)

        st.markdown('<span class="scada-label">ORGANIZATION</span>', unsafe_allow_html=True)
        st.markdown('<div class="scada-org-text">Far Eastern New Century (FENC)</div>', unsafe_allow_html=True)

        st.markdown('<span class="scada-label">ACCOUNT ID</span>', unsafe_allow_html=True)
        st.text_input("", value="Audit_HQ_Admin", label_visibility="collapsed")

        st.markdown('<span class="scada-label">PASSWORD</span>', unsafe_allow_html=True)
        pwd = st.text_input("", type="password", label_visibility="collapsed")

        if st.button("SIGN IN", type="primary", use_container_width=True):
            if pwd == "AUDIT@01":
                st.session_state["password_correct"] = True
                st.rerun()
            elif pwd != "":
                st.error("❌ ACCESS DENIED — Invalid credentials")

        st.markdown("""
        <div class="scada-footer">
            <a href="#">Forgot Password</a>
             <span>•</span> 
            <a href="#">IT Support (ext. 6855)</a>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    return False

if not check_password():
    st.stop()

# ================================
# 📊 DASHBOARD 主系統（原功能保留）
# ================================
st.markdown("""
<style>
.stApp { background:#000 !important; color:#f5f5f7 !important; }
</style>
""", unsafe_allow_html=True)

st.title("Strategic Control Center")
st.caption("FENC Audit Headquarters")

st.success("✅ Login Successful — System Online")
