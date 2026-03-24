import streamlit as st
import twstock
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz
import requests
import urllib3
import yfinance as yf
import numpy as np
import os
import pickle

# === 0. 系統層級修復 ===
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
original_request = requests.Session.request
def patched_request(self, method, url, *args, **kwargs):
    kwargs['verify'] = False
    return original_request(self, method, url, *args, **kwargs)
requests.Session.request = patched_request

# ====================== TEJ 永久保存 ======================
DATA_DIR = "./data"
TEJ_FILE = os.path.join(DATA_DIR, "tej_data.pkl")

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def load_saved_tej_data():
    if os.path.exists(TEJ_FILE):
        try:
            with open(TEJ_FILE, "rb") as f:
                return pickle.load(f)
        except:
            return None
    return None

def save_tej_data(df):
    ensure_data_dir()
    try:
        with open(TEJ_FILE, "wb") as f:
            pickle.dump(df, f)
        return True
    except:
        return False

def clear_saved_tej_data():
    if os.path.exists(TEJ_FILE):
        os.remove(TEJ_FILE)
        return True
    return False

# ====================== TEJ 解析 ======================
@st.cache_data
def parse_tej_excel_files(uploaded_files):
    if not uploaded_files:
        return None
    all_dfs = []
    for uploaded_file in uploaded_files:
        try:
            dfs = pd.read_excel(uploaded_file, sheet_name=None)
            for sheet_name, df in dfs.items():
                df = df.copy()
                df.columns = [str(col).strip().replace('\n', '').replace('\r', '').replace(' ', '') for col in df.columns]
               
                col_mapping = {
                    '代號': 'stock_id',
                    '名稱': 'company_name',
                    '年/月': 'date',
                    '存貨及應收帳款/淨值': 'inv_ar_to_equity',
                    '應收帳款週轉次數': 'ar_turnover_times',
                    '總資產週轉次數': 'total_assets_turnover',
                    '平均收帳天數': 'ar_days',
                    '存貨週轉率（次）': 'inv_turnover_times',
                    '存貨週轉率(次)': 'inv_turnover_times',
                    '平均售貨天數': 'inv_days',
                    '固定資產週轉次數': 'fixed_assets_turnover',
                    '淨值週轉率（次）': 'equity_turnover',
                    '應付帳款付現天數': 'ap_days',
                    '淨營業週期（日）': 'net_operating_cycle',
                }
                df = df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns})
               
                if 'stock_id' not in df.columns and 'company_name' in df.columns:
                    df['stock_id'] = df['company_name'].str.extract(r'(\d{4})')
                if 'stock_id' in df.columns:
                    df['stock_id'] = df['stock_id'].astype(str).str.zfill(4)
               
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'], errors='coerce')
               
                numeric_cols = ['inv_ar_to_equity', 'ar_turnover_times', 'total_assets_turnover', 'ar_days',
                                'inv_turnover_times', 'inv_days', 'fixed_assets_turnover', 'equity_turnover',
                                'ap_days', 'net_operating_cycle']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
               
                if 'inv_turnover_times' in df.columns:
                    df['inv_days'] = (365 / df['inv_turnover_times']).round(1)
               
                all_dfs.append(df)
        except Exception as e:
            st.warning(f"檔案「{uploaded_file.name}」解析失敗：{str(e)}")
  
    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        sort_cols = [col for col in ['stock_id', 'date'] if col in combined.columns]
        if sort_cols:
            combined = combined.sort_values(sort_cols, ascending=[True] * len(sort_cols)).reset_index(drop=True)
        return combined
    return None

# === 1. 戰情室初始化 ===
st.set_page_config(page_title="FENC Audit | Executive Intelligence", layout="wide", initial_sidebar_state="expanded")
tw_tz = pytz.timezone('Asia/Taipei')

# === 登入介面 ===
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;800&family=Noto+Sans+TC:wght@300;400;500;700;800&display=swap');
        [data-testid="stSidebar"], header, [data-testid="collapsedControl"] {display: none !important;}
        .stApp { background-color: #0b0f19 !important; font-family: 'Poppins', 'Noto Sans TC', sans-serif !important; }
        .hero-title-solid { font-size: 70px; font-weight: 800; color: #ffffff; line-height: 1.1; margin-bottom: 0; letter-spacing: -2px; }
        .hero-title-outline { font-size: 55px; font-weight: 900; color: transparent; -webkit-text-stroke: 1.5px #ffffff; line-height: 1.2; margin-top: 5px; margin-bottom: 50px; }
        .label-dashboard { background-color: #1e293b; color: #38bdf8; padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 14px; display: inline-block; border: 1px solid #38bdf8; }
        div[data-baseweb="input"] > div { border: 1px solid #334155 !important; background-color: #1e293b !important; border-radius: 8px !important; height: 52px !important; color: white !important;}
        button[kind="primary"] { background-color: #38bdf8 !important; color: #0f172a !important; border-radius: 8px !important; height: 50px !important; font-weight: 800 !important; }
    </style>
    """, unsafe_allow_html=True)
    col_left, spacer, col_right = st.columns([1.1, 0.2, 0.9])
    with col_left:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div class="hero-title-solid">Audit. Department</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-title-outline">Far Eastern Group</div>', unsafe_allow_html=True)
        st.markdown('<div class="label-dashboard">Executive Intelligence</div>', unsafe_allow_html=True)
    with col_right:
        st.markdown('<div style="font-size: 28px; color: #ffffff; font-weight: 900; margin-bottom: 2px;">遠東聯合稽核總部</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size: 16px; font-weight: 600; color: #94a3b8; margin-bottom: 30px;">Executive Login</div>', unsafe_allow_html=True)
        st.text_input("Customer ID", value="fenc07822", label_visibility="collapsed", key="acc_id")
        pwd = st.text_input("Passcode", type="password", label_visibility="collapsed", key="pwd")
        if st.button("Secure Login ──", type="primary", use_container_width=True):
            if pwd == "AUDIT@01":
                st.session_state["password_correct"] = True
                st.rerun()
            elif pwd != "":
                st.error("Invalid credentials")
    return False

if not check_password():
    st.stop()

# === 2. 核心 UI 樣式 (財經科技感) ===
st.markdown("""
    <style>
        html, body, [class*="css"] { font-family: 'Noto Sans TC', 'Microsoft JhengHei', sans-serif !important; }
        .main-title { font-size: 2.2rem; font-weight: 800; color: #0f172a; text-align: center; margin: 1rem 0; letter-spacing: 1px;}
        .sub-title { font-size: 1rem; color: #64748b; text-align: center; margin-bottom: 2rem; font-weight: 500;}
        .metric-card { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; text-align: center;}
        .metric-title { font-size: 14px; color: #64748b; font-weight: 600; margin-bottom: 8px;}
        .metric-value { font-size: 32px; font-weight: 800; color: #0f172a; font-family: 'Courier New', Courier, monospace;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">遠東集團 (Far Eastern Group)</div><div class="sub-title">聯合稽核總部 ｜ 戰略決策儀表板</div>', unsafe_allow_html=True)

# === 3. 深度戰略連動註解庫 ===
MACRO_IMPACT = {
    "🇹🇼 台灣加權指數": "台灣加權指數為台灣整體經濟及半導體產業景氣的綜合指標。主要與台積電等科技巨頭連動，可作為評估外資資金流向及國內資本市場活力的關鍵參考。",
    "🇺🇸 S&P 500": "S&P 500 指數涵蓋美國前 500 大企業，代表美國實體經濟的全貌。其涵蓋多樣產業，為全球長期資金配置及美股市場多空趨勢判斷的基準指標。",
    "🇺🇸 SOX (費半)": "費城半導體指數為全球半導體產業鏈的核心指標，涵蓋晶片設計至設備製造等環節，可精準預測電子業庫存循環及終端需求趨勢。"
}

# === 4. 板塊分類字典 ===
market_categories = {
    "📈 總體經濟與大盤 (宏觀指標)": {
        "🇹🇼 台灣加權指數": "^TWII", "🇺🇸 S&P 500": "^GSPC", "🇺🇸 SOX (費半)": "^SOX"
    },
    "🏢 遠東集團核心事業體": {
        "👕 1402 遠東新": "1402", "🏗️ 1102 亞泥": "1102", "🚢 2606 裕民": "2606", "🧵 1460 宏遠": "1460",
        "🛍️ 2903 遠百": "2903", "📱 4904 遠傳": "4904", "🧪 1710 東聯": "1710", "🏦 2845 遠東銀": "2845"
    }
}

# === 5. API 與真實資料抓取模組 ===
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
        hist = tk.history(period="6mo")
        data_list = [{'date': idx.strftime('%Y-%m-%d'), 'volume': float(row['Volume']), 'open': float(row['Open']), 'high': float(row['High']), 'low': float(row['Low']), 'close': float(row['Close'])} for idx, row in hist.iterrows()]
        return data_list
    except: return None

def plot_daily_k(df):
    if df.empty: return None
    df = df.copy()
    df.set_index(pd.to_datetime(df['date']), inplace=True)
    df = df.tail(120)
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#ef4444', increasing_fillcolor='#ef4444',
        decreasing_line_color='#22c55e', decreasing_fillcolor='#22c55e',
        name="日K"
    )])
    fig.update_layout(title="<b>📊 歷史價格走勢 (近半年)</b>", xaxis_rangeslider_visible=False, height=380, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor='#ffffff', plot_bgcolor='#ffffff')
    return fig

# === 6. 左側選單 ===
with st.sidebar:
    st.header("🎯 戰略監控目標")
    st.subheader("📤 TEJ 資料庫匯入")
    uploaded_files = st.file_uploader("TEJ 財報檔案", type=["xlsx", "xls"], accept_multiple_files=True, label_visibility="collapsed")
    if uploaded_files:
        with st.spinner("🔄 正在解析並永久保存 TEJ 資料..."):
            tej_df = parse_tej_excel_files(uploaded_files)
            if tej_df is not None and not tej_df.empty:
                st.session_state['tej_data'] = tej_df
                save_tej_data(tej_df)
                st.success("✅ TEJ 資料已保存")
    else:
        if 'tej_data' not in st.session_state:
            saved = load_saved_tej_data()
            if saved is not None:
                st.session_state['tej_data'] = saved
    
    st.markdown("---")
    selected_category = st.selectbox("板塊分類", list(market_categories.keys()))
    options_dict = market_categories[selected_category]
    option = st.radio("監控標的", list(options_dict.keys()))
    code = options_dict[option]
    is_tw_stock = code.isdigit()

# === 7. 價格顯示 ===
real_data = {'price': 0, 'high': '-', 'low': '-', 'open': '-', 'volume': '-'}
if is_tw_stock:
    try:
        real = twstock.realtime.get(code)
        if real['success']:
            info = real['realtime']
            latest = float(info['latest_trade_price']) if info['latest_trade_price'] != '-' else (float(info['open']) if info['open'] != '-' else 0.0)
            real_data.update({'price': latest})
    except: pass
    hist_data = fetch_twse_history_proxy(code)
else:
    hist_data = fetch_us_history(code)

df_daily = pd.DataFrame(hist_data) if hist_data else pd.DataFrame()
current_price = real_data['price']
if (current_price == 0 or current_price is None) and not df_daily.empty:
    current_price = df_daily.iloc[-1]['close']

prev_close = df_daily.iloc[-2]['close'] if len(df_daily) > 1 else (df_daily.iloc[-1]['close'] if not df_daily.empty else 0)
change = current_price - prev_close
pct = (change / prev_close) * 100 if prev_close != 0 else 0

st.markdown(f"""
<div style="background-color: #ffffff; padding: 25px; border-radius: 8px; margin-bottom: 25px; border-left: 6px solid {'#ef4444' if change >= 0 else '#22c55e'}; box-shadow: 0 2px 5px rgba(0,0,0,0.03);">
    <h2 style="margin:0; color:#475569; font-size: 1.25rem; font-weight: 800;">{option}</h2>
    <div style="display: flex; align-items: baseline; gap: 15px; margin-top: 8px;">
        <span style="font-size: 3.2rem; font-weight: 800; color: #0f172a; letter-spacing: -1px;">
            {"NT$" if is_tw_stock else ""} {current_price:,.2f}
        </span>
        <span style="font-size: 1.5rem; font-weight: 700; color: {'#ef4444' if change >= 0 else '#22c55e'};">{change:+.2f} ({pct:+.2f}%)</span>
    </div>
</div>
""", unsafe_allow_html=True)

if not df_daily.empty: st.plotly_chart(plot_daily_k(df_daily), use_container_width=True)

# === 8. TEJ 財務健檢與同業對標分析 ===
if is_tw_stock:
    st.divider()
    st.markdown("## 📊 TEJ 深度營運分析與同業對標 (Peer Comparison)")
    tej_df = st.session_state.get('tej_data', None)
  
    if tej_df is not None and not tej_df.empty:
        company_df = tej_df[tej_df['stock_id'] == str(code)].sort_values('date', ascending=False)
        if not company_df.empty:
            latest = company_df.iloc[0]
            company_name = latest.get('company_name', f'公司 {code}')
            
            # 定義同業與名單
            peer_dict = {'1402': '遠東新', '1409': '新纖', '1464': '得力', '1303': '南亞', '1718': '中纖'}
            all_target_ids = list(peer_dict.keys())
            
            # 抓取所有目標公司的最新財報
            all_latest_data = {}
            for pid in all_target_ids:
                p_df = tej_df[tej_df['stock_id'] == pid].sort_values('date', ascending=False)
                if not p_df.empty:
                    all_latest_data[pid] = p_df.iloc[0]

            # 指標定義
            indicators_dict = {
                'inv_ar_to_equity': {'name': '存貨及應收帳款/淨值', 'better': 'lower'},
                'ar_turnover_times': {'name': '應收帳款週轉次數', 'better': 'higher'},
                'total_assets_turnover': {'name': '總資產週轉次數', 'better': 'higher'},
                'ar_days': {'name': '平均收帳天數', 'better': 'lower'},
                'inv_turnover_times': {'name': '存貨週轉率', 'better': 'higher'},
                'inv_days': {'name': '平均售貨天數', 'better': 'lower'},
                'fixed_assets_turnover': {'name': '固定資產週轉次數', 'better': 'higher'},
                'equity_turnover': {'name': '淨值週轉率', 'better': 'higher'},
                'ap_days': {'name': '應付帳款付現天數', 'better': 'lower'},
                'net_operating_cycle': {'name': '淨營業週期', 'better': 'lower'}
            }
            
            # 計算產業平均 (作為基準)
            industry_avg = {}
            for key in indicators_dict.keys():
                vals = [all_latest_data[pid].get(key) for pid in all_latest_data if pd.notna(all_latest_data[pid].get(key))]
                industry_avg[key] = np.mean(vals) if vals else np.nan

            # 計算各公司分數 (滿分 100 分)
            # 修正邏輯：每個指標贏過或等於平均得 10 分，總共 10 個指標，最高 100 分。
            scores = {}
            for pid, data in all_latest_data.items():
                score = 0
                for key, info in indicators_dict.items():
                    val = data.get(key)
                    avg = industry_avg.get(key)
                    if pd.notna(val) and pd.notna(avg):
                        if info['better'] == 'higher' and val >= avg: score += 10
                        elif info['better'] == 'lower' and val <= avg: score += 10
                scores[pid] = score

            # --- 區塊 A：分數看板 ---
            st.markdown("### 🏆 產業經營能力綜合評分 (滿分 100 分)")
            cols = st.columns(len(all_latest_data))
            for i, (pid, score) in enumerate(scores.items()):
                comp_name = peer_dict.get(pid, pid)
                color = "#22c55e" if score >= 60 else "#ef4444"
                highlight = "box-shadow: 0 0 15px rgba(56, 189, 248, 0.5); border: 2px solid #38bdf8;" if pid == str(code) else ""
                with cols[i]:
                    st.markdown(f"""
                    <div class="metric-card" style="{highlight}">
                        <div class="metric-title">{comp_name} ({pid})</div>
                        <div class="metric-value" style="color: {color};">{score}</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # --- 區塊 B：最新關鍵指標數據表 ---
            st.markdown("### 📝 最新關鍵指標明細")
            table_data = {"指標": [info['name'] for info in indicators_dict.values()]}
            for pid in all_target_ids:
                if pid in all_latest_data:
                    c_data = all_latest_data[pid]
                    col_name = f"{peer_dict[pid]} ({pid})"
                    table_data[col_name] = [
                        round(c_data.get(k, np.nan), 2) if pd.notna(c_data.get(k)) else "-" 
                        for k in indicators_dict.keys()
                    ]
            
            metrics_df = pd.DataFrame(table_data)
            st.dataframe(metrics_df, use_container_width=True, hide_index=True)

            # --- 區塊 C：新增專業科技感 X-Y 軸圖表 (營運效率三本柱) ---
            st.markdown("### 📈 核心營運效率對比 (X-Y 軸分析圖)")
            
            # 選取三個關鍵指標來畫圖
            chart_metrics = ['ar_turnover_times', 'inv_turnover_times', 'total_assets_turnover']
            chart_metric_names = [indicators_dict[m]['name'] for m in chart_metrics]
            
            fig_xy = go.Figure()
            colors = ['#38bdf8', '#818cf8', '#34d399', '#fbbf24', '#f87171']
            
            for i, pid in enumerate(all_target_ids):
                if pid in all_latest_data:
                    y_values = [all_latest_data[pid].get(m, 0) for m in chart_metrics]
                    fig_xy.add_trace(go.Bar(
                        x=chart_metric_names,
                        y=y_values,
                        name=f"{peer_dict[pid]}",
                        marker_color=colors[i % len(colors)],
                        text=[f"{v:.2f}" if v != 0 else "-" for v in y_values],
                        textposition='auto',
                        textfont=dict(size=12, color='white')
                    ))

            fig_xy.update_layout(
                barmode='group',
                height=500,
                plot_bgcolor='#0b0f19', # 科技感深色背景
                paper_bgcolor='#ffffff',
                margin=dict(l=20, r=20, t=50, b=20),
                xaxis=dict(
                    title=dict(text="效率指標 (次/年)", font=dict(size=14, color="#64748b")),
                    tickfont=dict(size=14, color="#1e293b", weight="bold"),
                    gridcolor="#334155",
                    showgrid=False
                ),
                yaxis=dict(
                    title=dict(text="週轉次數", font=dict(size=14, color="#64748b")),
                    gridcolor="#e2e8f0",
                    tickfont=dict(size=12)
                ),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5,
                    font=dict(size=13, color="#1e293b")
                ),
                font=dict(family="Noto Sans TC")
            )
            
            st.plotly_chart(fig_xy, use_container_width=True)

        else:
            st.warning("TEJ 資料中尚未找到該公司資訊。")
    else:
        st.info("請先上傳 TEJ 檔案以啟用分析。")

update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f'<div style="text-align:center; color:#94a3b8; font-size:0.8rem; margin-top:3rem;">系統更新時間：{update_time} ｜ 遠東聯合稽核總部</div>', unsafe_allow_html=True)
