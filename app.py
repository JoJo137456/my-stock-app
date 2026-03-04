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

# === 全新工業 SCADA 風格登入介面（參考 Dribbble / Behance 現代控制室設計） ===
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True

    # 背景圖（請務必使用你這張控制面板照片當 bg.jpg）
    if os.path.exists('bg.jpg'):
        with open('bg.jpg', 'rb') as f:
            encoded_bg = base64.b64encode(f.read()).decode()
        bg_css = f"""
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
            background: linear-gradient(rgba(0,0,0,0.75), rgba(0,0,0,0.85));
            z-index: -1;
        }}
        </style>
        """
        st.markdown(bg_css, unsafe_allow_html=True)

    # 新 SCADA 工業風 CSS（高對比、無黑框、超清晰）
    st.markdown("""
    <style>
        [data-testid="stSidebar"], header, [data-testid="collapsedControl"] {display: none !important;}
        
        /* 主卡片 - 玻璃 + 金屬工業感 */
        .scada-card {
            background: rgba(15, 18, 25, 0.92);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border: 2px solid #00ff9f;
            border-radius: 18px;
            padding: 60px 55px 50px;
            max-width: 460px;
            margin: 90px auto 40px;
            box-shadow: 
                0 0 40px rgba(0, 255, 159, 0.25),
                0 25px 60px rgba(0, 0, 0, 0.8);
        }
        
        .scada-title {
            font-size: 42px;
            font-weight: 900;
            color: #ffffff;
            text-align: center;
            letter-spacing: 3px;
            margin-bottom: 8px;
            text-shadow: 0 0 15px #00ff9f;
        }
        .scada-subtitle {
            font-size: 17px;
            color: #a0f0d0;
            text-align: center;
            margin-bottom: 50px;
            font-weight: 500;
        }
        
        /* 標籤 - 工業黃綠色 */
        .scada-label {
            font-size: 14px;
            font-weight: 700;
            color: #00ff9f;
            margin: 22px 0 10px 4px;
            letter-spacing: 2px;
            text-transform: uppercase;
            display: block;
        }
        
        /* 輸入框 - 深色高對比（絕對清晰） */
        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div {
            background-color: rgba(30, 35, 45, 0.95) !important;
            border: 1px solid #00ff9f !important;
            border-radius: 12px !important;
            height: 58px !important;
            box-shadow: inset 0 2px 6px rgba(0,0,0,0.6);
        }
        div[data-baseweb="input"] input {
            color: #ffffff !important;
            font-size: 18px !important;
            font-weight: 500 !important;
        }
        div[data-baseweb="input"]:focus-within > div {
            border-color: #00ff9f !important;
            box-shadow: 0 0 0 4px rgba(0, 255, 159, 0.4) !important;
        }
        
        /* Sign In 按鈕 - 電光藍 */
        button[kind="primary"] {
            background: linear-gradient(90deg, #00b8ff, #0090ff) !important;
            color: #ffffff !important;
            font-size: 18px !important;
            font-weight: 700 !important;
            height: 60px !important;
            border-radius: 12px !important;
            border: none !important;
            margin-top: 30px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
        }
        button[kind="primary"]:hover {
            background: linear-gradient(90deg, #00ff9f, #00b8ff) !important;
            box-shadow: 0 0 30px rgba(0, 255, 159, 0.6);
            transform: scale(1.03);
        }
        
        /* 底部連結 */
        .scada-footer {
            text-align: center;
            margin-top: 45px;
            font-size: 15px;
            color: #88ccaa;
        }
        .scada-footer a {
            color: #00ff9f;
            text-decoration: none;
        }
        .scada-footer a:hover { text-decoration: underline; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.65, 1])
    with col2:
        with st.container():
            st.markdown('<div class="scada-card">', unsafe_allow_html=True)
            
            st.markdown('<div class="scada-title">AUDIT HQ</div>', unsafe_allow_html=True)
            st.markdown('<div class="scada-subtitle">FENC Corporate Control Access</div>', unsafe_allow_html=True)
            
            st.markdown('<span class="scada-label">ORGANIZATION</span>', unsafe_allow_html=True)
            st.selectbox("", ["Far Eastern New Century (FENC)"], label_visibility="collapsed")
            
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
                <a href="#">Forgot Password</a>  •  <a href="#">IT Support (ext. 6855)</a>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

    return False

if not check_password():
    st.stop()

# === 以下為你原本的主儀表板程式碼（完全不變）===
st.markdown("""
    <style>
        .stApp { background: #000000 !important; color: #f5f5f7 !important; }
        .main-title { font-size: 2.6rem; font-weight: 700; color: #f5f5f7; text-align: center; margin: 1.5rem 0; letter-spacing: 1px;}
        .sub-title { font-size: 1.15rem; color: #86868b; text-align: center; margin-bottom: 2.5rem; font-weight: 400;}
        .chart-container {
            background: #1c1c1e; padding: 24px; border-radius: 20px;
            margin-bottom: 24px; border: 1px solid #38383a;
        }
        div[data-testid="metric-container"] {
            background-color: #1c1c1e; border: 1px solid #38383a; padding: 15px;
            border-radius: 16px; text-align: center;
        }
        div[data-testid="metric-container"] > div { color: #f5f5f7 !important; }
        div[data-testid="metric-container"] label { color: #86868b !important; font-weight: 500 !important; font-size: 0.85rem !important; text-transform: uppercase;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">Strategic Control Center</div><div class="sub-title">FENC Audit Headquarters</div>', unsafe_allow_html=True)

# （以下所有函數、市場類別、資料處理、UI 呈現部分完全保留你原本的程式碼，我這裡省略以節省空間，但實際複製時請把你原本從 def check_market_status 開始到最後的所有程式碼貼上）

# ... [把你原本從 def check_market_status 到最後一行的所有程式碼貼在這裡] ...

update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"<div style='text-align: center; color: #86868b; font-size: 0.8rem; margin-top: 40px;'>Last synced: {update_time} (CST)</div>", unsafe_allow_html=True)
