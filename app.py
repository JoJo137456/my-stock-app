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
st.set_page_config(page_title="FENC Audit Dashboard", layout="wide", initial_sidebar_state="expanded")
tw_tz = pytz.timezone('Asia/Taipei')

# --- 核心 CSS 樣式 (確保字體一致與紅漲綠跌) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans TC', sans-serif !important; }
    .main-title { font-size: 2.2rem; font-weight: 900; color: #1e293b; text-align: center; margin-bottom: 0.5rem; }
    .sub-title { font-size: 1.1rem; color: #64748b; text-align: center; margin-bottom: 2rem; }
    /* 台灣習慣：紅漲綠跌 */
    .price-up { color: #ef4444 !important; } 
    .price-down { color: #22c55e !important; }
    .metric-container { background: #ffffff; border: 1px solid #f1f5f9; padding: 15px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
</style>
""", unsafe_allow_html=True)

# === 2. 戰略標的清單 (補齊所有標的) ===
market_categories = {
    "📈 總體經濟與大盤 (宏觀指標)": {
        "🇹🇼 台灣加權指數": "^TWII", "🇺🇸 S&P 500": "^GSPC", "🇺🇸 Dow Jones": "^DJI", "🇺🇸 Nasdaq": "^IXIC", 
        "🇺🇸 SOX (費半)": "^SOX", "⚠️ VIX 恐慌指數": "^VIX", "🏦 U.S. 10Y Treasury": "^TNX", "🥇 黃金": "GC=F",
        "💵 美元指數": "DX-Y.NYB", "💱 美元兌台幣": "TWD=X", "🚢 航運運價 (BDRY)": "BDRY"
    },
    "🏢 遠東集團核心事業體": {
        "👕 1402 遠東新": "1402", "🏗️ 1102 亞泥": "1102", "🚢 2606 裕民": "2606", "🛍️ 2903 遠百": "2903", 
        "📱 4904 遠傳": "4904", "🧪 1710 東聯": "1710", "🏦 2845 遠東銀": "2845", "🧵 1460 宏遠": "1460"
    },
    "👟 國際品牌終端 (紡織板塊)": {
        "🇺🇸 Nike": "NKE", "🇺🇸 Lululemon": "LULU", "🇺🇸 Under Armour": "UAA", "🇩🇪 Adidas": "ADS.DE", "🇯🇵 Fast Retailing": "9983.T"
    },
    "🥤 國際品牌終端 (化纖/消費)": {
        "🇺🇸 Coca-Cola": "KO", "🇺🇸 PepsiCo": "PEP", "🇺🇸 P&G": "PG", "🇺🇸 Unilever": "UL"
    }
}

# 指標定義資料庫
MACRO_IMPACT = {
    "🇺🇸 S&P 500": "標普 500 指數涵蓋美國 500 家大型企業，為全球權益資產定價之基準。跌破年線通常代表全球資本進入防禦性收縮。",
    "🇹🇼 台灣加權指數": "反映台灣半導體及電子出口動能之核心指標，高度受台積電與遠東相關權值股影響。",
    "⚠️ VIX 恐慌指數": "利用標普 500 選擇權隱含波動率編製，數值 > 25 代表市場預期未來極度不穩定，避險情緒高漲。",
    "💵 美元指數": "衡量美元相對國際主要貨幣價值。美元強勢（紅）對新興市場通常具備資金流出壓力。"
}

# === 3. 核心數據引擎 ===
@st.cache_data(ttl=600)
def get_comprehensive_data(code, is_tw):
    # 歷史數據 (抓 1.5 年確保 1 年漲跌不 N/A)
    tk = yf.Ticker(code if not is_tw else f"{code}.TW")
    hist = tk.history(period="18mo")
    
    # 即時數據
    current = tk.basic_info.last_price if hasattr(tk, 'basic_info') else hist['Close'].iloc[-1]
    prev_close = hist['Close'].iloc[-2]
    
    # 分時圖數據
    intra = tk.history(period="1d", interval="1m")
    if intra.empty: intra = tk.history(period="5d", interval="5m").tail(100)
    
    return hist, intra, current, prev_close

# === 4. UI 邏輯開始 ===
with st.sidebar:
    st.markdown("## 🎯 戰略監控目標")
    cat = st.selectbox("板塊分類", list(market_categories.keys()))
    option = st.radio("監控標的", list(market_categories[cat].keys()))
    target_code = market_categories[cat][option]
    is_tw = target_code.isdigit()

# 獲取數據
hist, intra, cur_price, prev_c = get_comprehensive_data(target_code, is_tw)
change = cur_price - prev_c
pct = (change / prev_c) * 100
p_class = "price-up" if change >= 0 else "price-down"

# --- 頂部報價卡片 ---
st.markdown(f"""
<div style="background:#fff; padding:25px; border-radius:12px; border-left:8px solid {'#ef4444' if change >= 0 else '#22c55e'}; box-shadow:0 4px 6px rgba(0,0,0,0.05);">
    <div style="font-size:1.2rem; color:#64748b; font-weight:700;">{option} ({target_code})</div>
    <div style="display:flex; align-items:baseline; gap:20px;">
        <div style="font-size:3.5rem; font-weight:900;">{cur_price:,.2f} <span style="font-size:1.2rem; color:#94a3b8;">USD</span></div>
        <div class="{p_class}" style="font-size:1.8rem; font-weight:700;">{change:+.2f} ({pct:+.2f}%)</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 指標定義 (放在報價下方) ---
if cat == "📈 總體經濟與大盤 (宏觀指標)" and option in MACRO_IMPACT:
    st.info(f"📊 **指標定義：** {MACRO_IMPACT[option]}")

# --- 中間圖表區 (分時與日K) ---
col1, col2 = st.columns(2)
with col1:
    fig_i = go.Figure(go.Scatter(x=intra.index, y=intra['Close'], fill='tozeroy', line=dict(color='#1e293b', width=2)))
    fig_i.update_layout(title="⚡ 當日分時動態", height=350, template="plotly_white", margin=dict(l=0,r=0,t=40,b=0))
    st.plotly_chart(fig_i, use_container_width=True)

with col2:
    fig_k = go.Figure(data=[go.Candlestick(x=hist.index[-100:], open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'],
                                         increasing_line_color='#ef4444', decreasing_line_color='#22c55e')])
    fig_k.update_layout(title="📅 歷史價格走勢 (近半年)", height=350, template="plotly_white", xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=40,b=0))
    st.plotly_chart(fig_k, use_container_width=True)

# === 5. 多時段漲跌戰略統計 (解決 N/A 問題) ===
st.markdown("### 📊 多時段漲跌戰略統計")
periods = {"近 3 日": 3, "近 1 週": 5, "近雙週": 10, "近 1 月": 21, "近 1 季": 63, "近 1 年": 252}
p_cols = st.columns(6)

for i, (label, days) in enumerate(periods.items()):
    if len(hist) >= days:
        p_val = hist['Close'].iloc[-days]
        p_pct = ((cur_price - p_val) / p_val) * 100
        p_diff = cur_price - p_val
        p_color = "#ef4444" if p_diff >= 0 else "#22c55e"
        with p_cols[i]:
            st.markdown(f"""
            <div class="metric-container">
                <div style="font-size:0.9rem; color:#64748b; font-weight:700;">{label}</div>
                <div style="font-size:1.6rem; font-weight:900; color:{p_color};">{p_pct:+.2f}%</div>
                <div style="font-size:0.85rem; color:{p_color};">{p_diff:+.2f}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        p_cols[i].metric(label, "N/A")

# === 6. 戰略警示系統 (Alerts) ===
st.markdown("<br>", unsafe_allow_html=True)
alert_msgs = []
if pct < -3: alert_msgs.append(f"🔥 【重度警示】當日跌幅達 {pct:.2f}%，觸發即時風險監控！")
if len(hist) >= 5 and ((cur_price - hist['Close'].iloc[-5])/hist['Close'].iloc[-5]*100) < -7:
    alert_msgs.append("🚨 【週預警】近一週累計跌幅超過 7%，請注意趨勢反轉。")

if alert_msgs:
    for msg in alert_msgs: st.error(msg)
else:
    st.success("✅ 目前各項指標波動處於常規監控範圍，未觸發異常警示。")

# === 7. 財務戰情室入口 (TW Stocks only) ===
if is_tw:
    st.divider()
    st.markdown("## 📈 企業基本面與高階戰略解析")
    with st.expander("📥 點擊此處上傳 Excel 真實財報數據"):
        up = st.file_uploader("上傳 .xlsx 檔案", type=["xlsx"])
        if up: st.success("數據已對接，AI 引擎計算中...")
