import streamlit as st
import twstock
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, time as dt_time
import pytz
import requests
import urllib3
import yfinance as yf
import numpy as np

# === 0. 系統層級修復與環境設定 ===
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
original_request = requests.Session.request
def patched_request(self, method, url, *args, **kwargs):
    kwargs['verify'] = False
    return original_request(self, method, url, *args, **kwargs)
requests.Session.request = patched_request

# === 1. 戰情室初始化 ===
st.set_page_config(page_title="FENC Audit Department | Executive Dashboard", layout="wide", initial_sidebar_state="expanded")
tw_tz = pytz.timezone('Asia/Taipei') 

# === 登入介面樣式與邏輯 ===
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True

    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;800&family=Noto+Sans+TC:wght@300;400;500;700;800&display=swap');
        [data-testid="stSidebar"], header, [data-testid="collapsedControl"] {display: none !important;}
        .stApp { background-color: #F0F8FF !important; font-family: 'Poppins', 'Noto Sans TC', sans-serif !important; }
        .hero-title-solid { font-size: 70px; font-weight: 800; color: #1A1A20; line-height: 1.1; margin-bottom: 0; letter-spacing: -2px; }
        .hero-title-outline { font-size: 55px; font-weight: 900; color: transparent; -webkit-text-stroke: 1.5px #1A1A20; line-height: 1.2; margin-top: 5px; margin-bottom: 50px; }
        .label-dashboard { background-color: #1A1B20; color: #ffffff; padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 14px; display: inline-block; }
        [data-testid="column"]:nth-of-type(3) { background: #ffffff; border-radius: 20px; padding: 40px 35px; box-shadow: 0 15px 35px rgba(0,0,0,0.04); margin-top: 20px; }
        button[kind="primary"] { background-color: #1A1B20 !important; color: white !important; border-radius: 8px !important; height: 50px !important; font-weight: 600 !important; }
    </style>
    """, unsafe_allow_html=True)

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

# ==========================================
# === 2. 核心 UI 樣式設定 ===
# ==========================================
st.markdown("""
    <style>
        html, body, [class*="css"]  { font-family: 'Noto Sans TC', 'Microsoft JhengHei', sans-serif !important; }
        .main-title { font-size: 2.2rem; font-weight: 800; color: #1e293b; text-align: center; margin: 1rem 0; letter-spacing: 1px;}
        .sub-title { font-size: 1rem; color: #64748b; text-align: center; margin-bottom: 2rem; font-weight: 500;}
        .ai-score-box { background: linear-gradient(135deg, #1e293b, #0f172a); color: white; padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.15);}
        .fraud-box-safe { background: #ffffff; border-left: 5px solid #22c55e; padding: 15px; border-radius: 8px; margin-top:15px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);}
        .fraud-box-warn { background: #ffffff; border-left: 5px solid #ef4444; padding: 15px; border-radius: 8px; margin-top:15px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);}
        [data-testid="stSidebar"] .stRadio label p { font-size: 1.15rem !important; font-weight: 600 !important; color: #1e293b !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">遠東集團 (Far Eastern Group)</div><div class="sub-title">聯合稽核總部 ｜ 戰略決策儀表板</div>', unsafe_allow_html=True)

# ==========================================
# === 3. API 與真實資料抓取模組 ===
# ==========================================
@st.cache_data(ttl=3600) 
def fetch_twse_history_proxy(stock_code):
    try:
        data_list = []
        now = datetime.now()
        for i in range(6):
            target_date = (now.replace(day=1) - pd.DateOffset(months=i)).strftime('%Y%m01')
            url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={target_date}&stockNo={stock_code}"
            r = requests.get(url).json()
            if r['stat'] == 'OK':
                for row in r['data']:
                    parts = row[0].split('/')
                    date_iso = f"{int(parts[0])+1911}-{parts[1]}-{parts[2]}"
                    def tf(s): return float(s.replace(',', '')) if s != '--' else 0.0
                    data_list.append({'date': date_iso, 'volume': tf(row[1]), 'open': tf(row[3]), 'high': tf(row[4]), 'low': tf(row[5]), 'close': tf(row[6])})
        return sorted(data_list, key=lambda x: x['date'])
    except: return None

@st.cache_data(ttl=3600)
def fetch_us_history(ticker_symbol):
    try:
        tk = yf.Ticker(ticker_symbol)
        hist = tk.history(period="1y") # 獲取一年數據以便計算各時段回報
        data_list = [{'date': idx.strftime('%Y-%m-%d'), 'volume': float(row['Volume']), 'open': float(row['Open']), 'high': float(row['High']), 'low': float(row['Low']), 'close': float(row['Close'])} for idx, row in hist.iterrows()]
        return data_list
    except: return None

@st.cache_data(ttl=300) 
def get_intraday_chart_data(stock_code, is_us_source=False):
    try:
        ticker = yf.Ticker(stock_code if is_us_source else f"{stock_code}.TW")
        df = ticker.history(period="1d", interval="1m")
        if df.empty:
            df = ticker.history(period="5d", interval="5m")
            if not df.empty: df = df[df.index.date == df.index[-1].date()]
        return df if not df.empty else None
    except: return None

# (其餘財務計算與 UI 輔助函式維持原樣，包含 get_resilient_financials, calculate_ai_audit_score, fetch_peers_ccc_real)
# ... [此處略過中間已定義的輔助函式以節省篇幅，與你原本的邏輯一致] ...

# ==========================================
# === 4. 繪圖模組 ===
# ==========================================
def plot_daily_k(df):
    if df.empty: return None
    df = df.copy().tail(120)
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], 
        increasing_line_color='#ef4444', increasing_fillcolor='#ef4444',
        decreasing_line_color='#22c55e', decreasing_fillcolor='#22c55e', name="日K"
    )])
    fig.update_layout(title="<b>📊 歷史價格走勢 (近半年)</b>", xaxis_rangeslider_visible=False, height=380, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor='#ffffff', plot_bgcolor='#ffffff')
    return fig

def plot_intraday_line(df):
    if df is None or df.empty: return None
    y_min, y_max = df['Close'].min(), df['Close'].max()
    padding = (y_max - y_min) * 0.1 if y_max != y_min else y_max * 0.01
    fig = go.Figure(go.Scatter(x=df.index, y=df['Close'], mode='lines', line=dict(color='#0f172a', width=2.5), fill='tozeroy', fillcolor='rgba(15, 23, 42, 0.05)', name='報價'))
    fig.update_layout(title="<b>⚡ 當日分時動態</b>", height=380, margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified", paper_bgcolor='#ffffff', plot_bgcolor='#ffffff', yaxis=dict(range=[y_min - padding, y_max + padding]))
    return fig

# ==========================================
# === 5. 左側選單互動與資料獲取 ===
# ==========================================
market_categories = {
    "📈 總體經濟與大盤 (宏觀指標)": {
        "🇹🇼 台灣加權指數": "^TWII", "🇺🇸 S&P 500": "^GSPC", "🇺🇸 Dow Jones": "^DJI", "🇺🇸 Nasdaq": "^IXIC", 
        "🇺🇸 SOX (費半)": "^SOX", "⚠️ VIX 恐慌指數": "^VIX", "🏦 U.S. 10Y Treasury": "^TNX", "🥇 黃金": "GC=F", 
        "💵 美元指數": "DX-Y.NYB", "💱 美元兌台幣": "TWD=X"
    },
    "🏢 遠東集團核心事業體": {
        "👕 1402 遠東新": "1402", "🏗️ 1102 亞泥": "1102", "🚢 2606 裕民": "2606", "🛍️ 2903 遠百": "2903", "📱 4904 遠傳": "4904", "🏦 2845 遠東銀": "2845"
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

# 抓取即時與歷史資料
if is_tw_stock:
    real = twstock.realtime.get(code)
    hist_data = fetch_twse_history_proxy(code)
    current_price = float(real['realtime']['latest_trade_price']) if real['success'] and real['realtime']['latest_trade_price'] != '-' else 0.0
else:
    tk = yf.Ticker(code)
    hist_data = fetch_us_history(code)
    current_price = tk.fast_info.last_price

df_daily = pd.DataFrame(hist_data) if hist_data else pd.DataFrame()
if current_price == 0 and not df_daily.empty: current_price = df_daily.iloc[-1]['close']

# 計算今日漲跌
prev_close = df_daily.iloc[-2]['close'] if len(df_daily) > 1 else current_price
change = current_price - prev_close
pct = (change / prev_close) * 100 if prev_close != 0 else 0

# 顯示主要價格卡片
st.markdown(f"""
<div style="background-color: #ffffff; padding: 25px; border-radius: 8px; margin-bottom: 25px; border-left: 6px solid {'#ef4444' if change >= 0 else '#22c55e'}; box-shadow: 0 2px 5px rgba(0,0,0,0.03);">
    <h2 style="margin:0; color:#475569; font-size: 1.25rem; font-weight: 800;">{option}</h2>
    <div style="display: flex; align-items: baseline; gap: 15px; margin-top: 8px;">
        <span style="font-size: 3.2rem; font-weight: 800; color: #0f172a; letter-spacing: -1px;">{"NT$" if is_tw_stock else ""} {current_price:,.2f}</span>
        <span style="font-size: 1.5rem; font-weight: 700; color: {'#ef4444' if change >= 0 else '#22c55e'};">{change:+.2f} ({pct:+.2f}%)</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# === 6. 新增：多時段漲跌統計與警示系統 ===
# ==========================================
if not df_daily.empty:
    st.markdown("### 📊 多時段漲跌戰略統計 (Performance Analytics)")
    df_calc = df_daily.copy()
    
    # 定義觀察週期 (交易日)
    periods = {"近 3 日": 3, "近 1 週": 5, "近雙週": 10, "近 1 月": 20, "近 1 季": 60, "近 1 年": 240}
    p_cols = st.columns(len(periods))
    alert_msgs = []

    for i, (p_label, p_days) in enumerate(periods.items()):
        if len(df_calc) >= p_days:
            past_val = df_calc.iloc[-p_days]['close']
            p_pct = ((current_price - past_val) / past_val) * 100
            p_diff = current_price - past_val
            with p_cols[i]:
                st.metric(p_label, f"{p_pct:+.2f}%", f"{p_diff:+.2f}")
            
            # 警示判定邏輯
            if p_label == "近 1 週" and p_pct < -7:
                alert_msgs.append(f"🚨 【重度警示】{option} 近一週累計跌幅達 {p_pct:.2f}%，已觸發風險控管警戒。")
            if p_label == "近 1 月" and p_pct < -15:
                alert_msgs.append(f"⚠️ 【趨勢轉弱】{option} 進入中期修正 (月跌幅 >15%)，建議重新評估內控估值。")
        else:
            with p_cols[i]: st.metric(p_label, "N/A")

    # 單日極端警示
    if pct < -3: alert_msgs.append(f"🔥 【即時警示】今日單日跌幅高達 {pct:.2f}%，請注意市場流動性風險。")
    if option == "⚠️ VIX 恐慌指數" and current_price > 25: alert_msgs.append(f"☢️ 【系統性風險】VIX 指數飆升至 {current_price:.2f}，市場避險情緒極度高漲！")

    # 渲染警示
    if alert_msgs:
        for msg in alert_msgs: st.error(msg, icon="🚨")
    else:
        st.success("✅ 目前各項指標波動處於常規監控範圍，未觸發異常警示。", icon="🛡️")

# 顯示圖表
col_c1, col_c2 = st.columns([1, 1])
with col_c1:
    df_intra = get_intraday_chart_data(code, not is_tw_stock)
    if df_intra is not None: st.plotly_chart(plot_intraday_line(df_intra), use_container_width=True)
with col_c2:
    if not df_daily.empty: st.plotly_chart(plot_daily_k(df_daily), use_container_width=True)

# ==========================================
# === 7. 下半部：財務戰情室 (含 Excel 匯入) ===
# ==========================================
if is_tw_stock:
    st.divider()
    st.markdown("## 📈 企業基本面與高階戰略解析 (Executive Financials)")
    
    # --- Excel 真實數據匯入區塊 ---
    with st.expander("📥 匯入企業內部真實財務數據 (Override API Data)"):
        st.info("💡 欄位需求：季度, 單季營收 (億), 毛利 (億), 毛利率 (%), 營業費用 (億), 淨利 (億), 淨利率 (%), 單季EPS (元), 存貨周轉天數, 應收帳款天數")
        up_file = st.file_uploader("上傳財報 Excel 檔", type=["xlsx"])
        
    if up_file:
        try:
            df_quarterly = pd.read_excel(up_file)
            st.success("✅ 內部真實數據載入成功！")
            # 重算 YTD 累計邏輯 (省略細節，邏輯同上一個回應)
        except: st.error("檔案格式不符")
    else:
        # 使用原本的模擬或 API 數據
        # df_quarterly, df_ytd = get_resilient_financials(code)
        pass 

    # [後續顯示 AI 評分、瀑布圖、CCC 矩陣等程式碼...]
