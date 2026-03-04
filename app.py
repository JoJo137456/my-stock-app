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

# === 0. 系統層級修復 ===
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
original_request = requests.Session.request
def patched_request(self, method, url, *args, **kwargs):
    kwargs['verify'] = False
    return original_request(self, method, url, *args, **kwargs)
requests.Session.request = patched_request

# === 1. 戰情室初始化 ===
st.set_page_config(page_title="遠東集團_高階戰略戰情室", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei') 

# === 1.5 安全防禦機制 (高對比實用主義登入介面) ===
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    # 載入大樓背景圖
    if os.path.exists('bg.jpg'):
        with open('bg.jpg', 'rb') as f:
            encoded_bg = base64.b64encode(f.read()).decode()
        bg_css = f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded_bg}") !important;
            background-size: cover !important;
            background-position: center !important;
            background-repeat: no-repeat !important;
        }}
        </style>
        """
        st.markdown(bg_css, unsafe_allow_html=True)
        
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] {display: none;}
            [data-testid="collapsedControl"] {display: none;}
            header {visibility: hidden;}
            
            /* 實體的深灰底框，阻絕背景干擾 */
            [data-testid="stVerticalBlockBorderWrapper"] {
                background-color: #555555 !important;
                border-radius: 8px !important;
                border: 1px solid #444444 !important;
                box-shadow: 0px 10px 30px rgba(0,0,0,0.8) !important;
                padding: 40px 50px !important;
            }
            
            /* 輸入框：純白背景、深色邊框、黑色文字 */
            div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
                background-color: #ffffff !important;
                border: 2px solid #333333 !important;
                border-radius: 4px !important;
            }
            input, select { 
                color: #000000 !important; 
                font-size: 1.1rem !important;
                font-weight: bold !important;
                -webkit-text-fill-color: #000000 !important; 
            }
            
            /* 按鈕：黃底黑字 */
            button[kind="primary"] {
                background-color: #FFC107 !important; 
                color: #000000 !important; 
                font-weight: 800 !important;
                font-size: 1.3rem !important;
                border: none !important;
                border-radius: 4px !important;
                padding: 10px !important;
            }
            button[kind="primary"]:hover {
                background-color: #E0A800 !important;
            }
        </style>
        """, unsafe_allow_html=True
    )

    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1]) 
    
    with col2:
        with st.container(border=True):
            # 標題
            st.markdown("<h2 style='text-align: center; color: #93C5FD; font-weight: 900; margin-bottom: 30px; letter-spacing: 2px; text-shadow: 2px 2px 4px rgba(0,0,0,0.8); font-size: 2.5rem;'>員工自助 / 戰略儀表板</h2>", unsafe_allow_html=True)
            
            # 使用 Emoji 加上黃色字體，模擬原圖左側的黃色區塊視覺效果
            st.markdown("<div style='background-color: #FFC107; color: #000000; display: inline-block; padding: 5px 15px; border-radius: 4px; font-weight: 800; margin-bottom: 5px;'>🏢 COMPANY</div>", unsafe_allow_html=True)
            st.selectbox("company", ["FENC 遠東新世紀股份"], label_visibility="collapsed")
            
            st.markdown("<div style='background-color: #FFC107; color: #000000; display: inline-block; padding: 5px 15px; border-radius: 4px; font-weight: 800; margin-top: 15px; margin-bottom: 5px;'>👤 ACCOUNT</div>", unsafe_allow_html=True)
            st.text_input("account", value="07822", label_visibility="collapsed")
            
            st.markdown("<div style='background-color: #FFC107; color: #000000; display: inline-block; padding: 5px 15px; border-radius: 4px; font-weight: 800; margin-top: 15px; margin-bottom: 5px;'>🔑 PASSWORD</div>", unsafe_allow_html=True)
            pwd = st.text_input("password", type="password", label_visibility="collapsed")
            
            # 說明文字
            st.markdown("""
                <div style='font-size: 0.85rem; color: #ffffff; margin-top: 20px; margin-bottom: 25px; line-height: 1.6;'>
                密碼預設：<br>
                紡織各廠/管貿單位/遠資(同公司開機或e-mail密碼)<br>
                化纖新埔及觀音廠(同化纖廠請假加班密碼)<br>
                從業員為身分證字號(開頭第一碼需大寫)
                </div>
            """, unsafe_allow_html=True)
            
            col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
            with col_btn3:
                if st.button("Login", type="primary", use_container_width=True):
                    if pwd == "AUDIT@01":
                        st.session_state["password_correct"] = True
                        st.rerun()
                    elif pwd != "":
                        st.error("🚫 密碼錯誤，拒絕存取。")
            
            st.markdown("<div style='display: flex; justify-content: space-around; margin-top: 20px;'><a href='#' style='color: #FFC107; font-weight: bold; text-decoration: none;'>忘記密碼</a><a href='#' style='color: #FFC107; font-weight: bold; text-decoration: none;'>登入密碼?</a></div>", unsafe_allow_html=True)

    return False

if not check_password():
    st.stop()


# === 2. 核心功能模組 ===
# (後方儀表板主邏輯保持不變)
st.markdown('<div class="main-title">FAR EASTERN GROUP</div><div class="sub-title">聯合稽核總部 ｜ 戰略決策儀表板</div>', unsafe_allow_html=True)
