import streamlit as st
import twstock
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
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

# --- 登入介面邏輯 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]: return True

    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&family=Noto+Sans+TC:wght@300;400;700;800&display=swap');
        .stApp { background-color: #F0F8FF !important; font-family: 'Poppins', 'Noto Sans TC', sans-serif !important; }
        .hero-title-solid { font-size: 60px; font-weight: 800; color: #1A1A20; line-height: 1.1; }
        .label-dashboard { background-color: #1A1B20; color: #ffffff; padding: 10px 25px; border-radius: 8px; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

    col_left, spacer, col_right = st.columns([1.1, 0.2, 0.9])
    with col_left:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div class="hero-title-solid">Audit. Dept</div>', unsafe_allow_html=True)
        st.markdown('<div class="label-dashboard">Executive Intelligence</div>', unsafe_allow_html=True)
    with col_right:
        st.markdown('### 遠東聯合稽核總部')
        st.text_input("Customer ID", value="fenc07822", key="acc_id")
        pwd = st.text_input("Passcode", type="password", key="pwd")
        if st.button("Secure Login", type="primary"):
            if pwd == "AUDIT@01":
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("Invalid credentials")
    return False

if not check_password(): st.stop()

# === 2. 核心 UI 與 顏色定義 ===
# 台灣標準：上漲紅 (#ef4444), 下跌綠 (#22c55e)
st.markdown("""
    <style>
        .main-title { font-size: 2.2rem; font-weight: 800; color: #1e293b; text-align: center; margin: 1rem 0;}
        .sub-title { font-size: 1rem; color: #64748b; text-align: center; margin-bottom: 2rem;}
        .alert-card { background: #fff; border-left: 5px solid #3b82f6; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">遠東集團 (Far Eastern Group)</div><div class="sub-title">聯合稽核總部 ｜ 戰略決策儀表板</div>', unsafe_allow_html=True)

# === 3. 數據抓取模組 (強化近一年數據穩定性) ===
@st.cache_data(ttl=3600) 
def fetch_twse_history_full(stock_code):
    try:
        data_list = []
        now = datetime.now()
        # 抓取過去 14 個月資料確保計算一年漲跌幅 (約 250 交易日)
        for i in range(14):
            target_date = (now.replace(day=1) - pd.DateOffset(months=i)).strftime('%Y%m01')
            url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={target_date}&stockNo={stock_code}"
            r = requests.get(url, timeout=10).json()
            if r.get('stat') == 'OK':
                for row in r['data']:
                    parts = row[0].split('/')
                    date_iso = f"{int(parts[0])+1911}-{parts[1]}-{parts[2]}"
                    def tf(s): return float(s.replace(',', '')) if s != '--' else 0.0
                    data_list.append({'date': date_iso, 'open': tf(row[3]), 'high': tf(row[4]), 'low': tf(row[5]), 'close': tf(row[6])})
        return sorted(data_list, key=lambda x: x['date'])
    except: return []

@st.cache_data(ttl=3600)
def fetch_us_history_full(ticker_symbol):
    try:
        tk = yf.Ticker(ticker_symbol)
        hist = tk.history(period="2y") # 抓兩年最穩
        return [{'date': idx.strftime('%Y-%m-%d'), 'open': row['Open'], 'high': row['High'], 'low': row['Low'], 'close': row['Close']} for idx, row in hist.iterrows()]
    except: return []

# === 4. 戰略板塊定義 (重啟四個選項) ===
market_categories = {
    "📈 總體經濟與大盤 (宏觀指標)": {
        "🇹🇼 台灣加權指數": "^TWII", "🇺🇸 S&P 500": "^GSPC", "🇺🇸 Dow Jones": "^DJI", "🇺🇸 Nasdaq": "^IXIC", 
        "🇺🇸 SOX (費半)": "^SOX", "⚠️ VIX 恐慌指數": "^VIX", "🏦 U.S. 10Y Treasury": "^TNX", "🥇 黃金": "GC=F"
    },
    "🏢 遠東集團核心事業體": {
        "👕 1402 遠東新": "1402", "🏗️ 1102 亞泥": "1102", "🚢 2606 裕民": "2606", "🛍️ 2903 遠百": "2903", "📱 4904 遠傳": "4904", "🏦 2845 遠東銀": "2845"
    },
    "👟 國際品牌終端 (紡織板塊對標)": {
        "🇺🇸 Nike": "NKE", "🇺🇸 Under Armour": "UAA", "🇺🇸 Lululemon": "LULU", "🇩🇪 Adidas": "ADS.DE"
    },
    "🥤 國際品牌終端 (化纖板塊對標)": {
        "🇺🇸 Coca-Cola": "KO", "🇺🇸 PepsiCo": "PEP", "🇺🇸 Procter & Gamble": "PG"
    }
}

with st.sidebar:
    st.header("🎯 戰略監控目標")
    selected_category = st.selectbox("板塊分類", list(market_categories.keys()))
    st.markdown("---")
    options_dict = market_categories[selected_category]
    option = st.radio("監控標的", list(options_dict.keys()))
    code = options_dict[option]
    is_tw_stock = code.isdigit()

# 獲取資料
if is_tw_stock:
    hist_data = fetch_twse_history_full(code)
else:
    hist_data = fetch_us_history_full(code)

df_daily = pd.DataFrame(hist_data)
if not df_daily.empty:
    current_price = df_daily.iloc[-1]['close']
    prev_close = df_daily.iloc[-2]['close'] if len(df_daily) > 1 else current_price
    change = current_price - prev_close
    pct = (change / prev_close) * 100
    
    # 主要價格顯示 (紅漲綠跌)
    main_color = "#ef4444" if change >= 0 else "#22c55e"
    st.markdown(f"""
    <div style="background-color: #ffffff; padding: 25px; border-radius: 8px; margin-bottom: 25px; border-left: 10px solid {main_color}; box-shadow: 0 2px 5px rgba(0,0,0,0.03);">
        <h2 style="margin:0; color:#475569;">{option} ({code})</h2>
        <div style="display: flex; align-items: baseline; gap: 15px; margin-top: 8px;">
            <span style="font-size: 3.5rem; font-weight: 800; color: #0f172a;">{current_price:,.2f}</span>
            <span style="font-size: 1.8rem; font-weight: 700; color: {main_color};">{change:+.2f} ({pct:+.2f}%)</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # === 5. 多時段漲跌統計與警示標準 ===
    st.markdown("### 📊 多時段漲跌戰略統計 (Performance Analytics)")
    
    # 確保計算時段有足夠數據，若無則顯示最近可用數據
    periods = {"近 3 日": 3, "近 1 週": 5, "近雙週": 10, "近 1 月": 21, "近 1 季": 63, "近 1 年": 252}
    p_cols = st.columns(len(periods))
    alert_msgs = []

    for i, (p_label, p_days) in enumerate(periods.items()):
        actual_days = min(len(df_daily), p_days)
        past_val = df_daily.iloc[-actual_days]['close']
        p_pct = ((current_price - past_val) / past_val) * 100
        p_diff = current_price - past_val
        
        # 顯示顏色：負數用綠色
        metric_color = "#ef4444" if p_diff >= 0 else "#22c55e"
        
        with p_cols[i]:
            st.markdown(f"""
                <div style="text-align: center; border: 1px solid #f1f5f9; padding: 10px; border-radius: 8px;">
                    <div style="font-size: 0.9rem; color: #64748b; font-weight: 600;">{p_label}</div>
                    <div style="font-size: 1.5rem; font-weight: 800; color: {metric_color};">{p_pct:+.2f}%</div>
                    <div style="font-size: 0.8rem; color: {metric_color};">{p_diff:+.2f}</div>
                </div>
            """, unsafe_allow_html=True)
            
        # 警示邏輯觸發
        if p_label == "近 1 週" and p_pct < -7: alert_msgs.append(f"🚨 【高風險】週跌幅 {p_pct:.2f}% 已超過戰略預警線 (7%)")
        if p_label == "近 1 月" and p_pct < -15: alert_msgs.append(f"⚠️ 【趨勢惡化】月跌幅 {p_pct:.2f}% 顯示中期基本面或市場情緒轉弱")

    # === 6. 警示標準與 ALERT ===
    with st.expander("🛡️ 戰略警示標準定義 (Audit Alert Criteria)", expanded=False):
        st.markdown("""
        | 警示等級 | 觸發條件 | 建議行動 |
        | :--- | :--- | :--- |
        | **🔴 重度警示** | 單日跌幅 > 3% 或 週跌幅 > 7% | 立即啟動專案審計，盤查財務健康度。 |
        | **🟡 中度警示** | 月跌幅 > 15% 或 VIX > 25 | 檢核供應鏈穩定度，評估風險溢價。 |
        | **🟢 正常監控** | 波動在 3% 以內 | 維持例行性監控與資料備份。 |
        """)

    if alert_msgs:
        for msg in alert_msgs: st.error(msg)
    elif pct < -3:
        st.error(f"🔥 【當日預警】單日跌幅 {pct:.2f}% 已觸發異常波動監控！")
    else:
        st.success("✅ 目前各項指標波動處於常規監控範圍，未觸發異常警示。")

    # 繪製 K 線圖
    fig = go.Figure(data=[go.Candlestick(
        x=df_daily['date'].tail(120), open=df_daily['open'].tail(120), 
        high=df_daily['high'].tail(120), low=df_daily['low'].tail(120), 
        close=df_daily['close'].tail(120),
        increasing_line_color='#ef4444', decreasing_line_color='#22c55e', name="日K"
    )])
    fig.update_layout(title="歷史走勢 (近半年)", xaxis_rangeslider_visible=False, height=450, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("⚠️ 無法獲取標的數據，請確認網路連線或標的代碼是否正確。")
