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

# CSS 美化 (高對比戰略深色風格 - 應用於主控台)
st.markdown("""
    <style>
        html, body, [class*="css"]  { 
            font-family: 'Microsoft JhengHei', 'Segoe UI', sans-serif !important; 
        }
        .stApp {
            background: #1a233a !important;
            color: #f8fafc !important;
        }
        .main-title { font-size: 2.2rem; font-weight: 800; color: #f8fafc; text-align: center; margin: 1rem 0; letter-spacing: 2px;}
        .sub-title { font-size: 1.1rem; color: #38bdf8; text-align: center; margin-bottom: 2rem; font-weight: 600; letter-spacing: 1px;}
        header {visibility: hidden;}
        .chart-container { 
            background: #151e2d; padding: 20px; border-radius: 12px; 
            box-shadow: 0 4px 20px rgba(0,0,0,0.5); margin-bottom: 20px; border: 1px solid #334155; 
        }
        .footer { text-align: center; color: #64748b; font-size: 0.85rem; margin-top: 3rem; }
        div[data-testid="metric-container"] {
            background-color: #151e2d; border: 1px solid #334155; padding: 15px;
            border-radius: 8px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        div[data-testid="metric-container"] > div { color: #f8fafc !important; }
        div[data-testid="metric-container"] label { color: #94a3b8 !important; font-weight: 600 !important; }
    </style>
""", unsafe_allow_html=True)

# === 1.5 安全防禦機制 (大樓背景 + 參考圖的高對比登入介面) ===
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
            
            /* 模仿第一張圖：深灰色實體底座，阻斷背景干擾 */
            [data-testid="stVerticalBlockBorderWrapper"] {
                background-color: #555555 !important; /* 實體的深灰色 */
                border-radius: 8px !important;
                border: 2px solid #444444 !important;
                box-shadow: 0 10px 40px rgba(0,0,0,0.8) !important;
                padding: 40px 50px !important;
            }
            
            /* 模仿第一張圖：輸入框強迫白底黑字，確保極致清晰 */
            div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
                background-color: #ffffff !important;
                border: 2px solid #cccccc !important;
                border-radius: 4px !important;
            }
            /* 輸入框內的文字顏色 */
            input, select { 
                color: #000000 !important; 
                font-size: 1.1rem !important;
                font-weight: bold !important;
                -webkit-text-fill-color: #000000 !important; /* 防止瀏覽器覆蓋 */
            }
            
            /* 模仿第一張圖：高對比的黃色登入按鈕 */
            button[kind="primary"] {
                background-color: #FBBF24 !important; /* 顯眼的黃色 */
                color: #000000 !important; /* 按鈕文字黑色 */
                font-weight: 800 !important;
                font-size: 1.2rem !important;
                border: none !important;
                border-radius: 4px !important;
                padding: 10px !important;
            }
            button[kind="primary"]:hover {
                background-color: #F59E0B !important;
            }
        </style>
        """, unsafe_allow_html=True
    )

    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1]) 
    
    with col2:
        with st.container(border=True):
            # 標題加上一點藍色與強烈的文字陰影，確保在任何情況下都跳得出來
            st.markdown("<h2 style='text-align: center; color: #93C5FD; font-weight: 900; margin-bottom: 30px; letter-spacing: 2px; text-shadow: 2px 2px 4px rgba(0,0,0,0.8); font-size: 2.5rem;'>聯稽總部戰略儀表板</h2>", unsafe_allow_html=True)
            
            st.markdown("<div style='color: #FBBF24; font-size: 1rem; margin-bottom: 5px; font-weight: 800; letter-spacing: 1px;'>🏢 COMPANY</div>", unsafe_allow_html=True)
            st.selectbox("company", ["遠東新世紀FENC"], label_visibility="collapsed")
            
            st.markdown("<div style='color: #FBBF24; font-size: 1rem; margin-bottom: 5px; margin-top: 20px; font-weight: 800; letter-spacing: 1px;'>👤 ACCOUNT</div>", unsafe_allow_html=True)
            # 把 disabled 拿掉，確保文字顏色是純黑的 (Streamlit 的 disabled 欄位會強制變灰)
            st.text_input("account", value="聯合稽核總部", label_visibility="collapsed")
            
            st.markdown("<div style='color: #FBBF24; font-size: 1rem; margin-bottom: 5px; margin-top: 20px; font-weight: 800; letter-spacing: 1px;'>🔒 PASSWORD</div>", unsafe_allow_html=True)
            pwd = st.text_input("password", type="password", label_visibility="collapsed")
            
            # 完全白色的提示字
            st.markdown("<p style='font-size: 0.9rem; color: #ffffff; margin-top: 15px; margin-bottom: 25px; line-height: 1.5;'>密碼預設：<br>同公司開機或e-mail密碼</p>", unsafe_allow_html=True)
            
            if st.button("Log in", type="primary", use_container_width=True):
                if pwd == "AUDIT@01":
                    st.session_state["password_correct"] = True
                    st.rerun()
                elif pwd != "":
                    st.error("🚫 密碼錯誤，拒絕存取。")
            
            # 純白高對比聯絡資訊
            st.markdown("<div style='font-size: 1.1rem; text-align: center; margin-top: 30px; font-weight: 800; color: #ffffff; text-shadow: 2px 2px 4px rgba(0,0,0,0.8); letter-spacing: 1px;'>若有問題，請聯繫李宗念先生(分機6855)</div>", unsafe_allow_html=True)

    return False

if not check_password():
    st.stop()


# === 2. 核心功能模組 ===
# (以下主控台的邏輯完全不動，請將原本 # === 2. 核心功能模組 === 以下的程式碼貼上即可，或是如果你需要完整版，可以直接延用上一次提供的後半段)
st.markdown('<div class="main-title">FAR EASTERN GROUP</div><div class="sub-title">聯合稽核總部 ｜ 戰略決策儀表板</div>', unsafe_allow_html=True)

# (為節省版面，後方資料處理與畫圖程式碼與上一版完全相同，請直接接續下去)
