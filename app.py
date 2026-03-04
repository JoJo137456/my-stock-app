import streamlit as st
import twstock
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, time as dt_time
import pytz
import requests
import urllib3
import yfinance as yf
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

# CSS 美化 (高對比戰略深色風格)
st.markdown("""
    <style>
        /* 全局字體與深色背景設定 */
        html, body, [class*="css"]  { 
            font-family: 'Microsoft JhengHei', 'Segoe UI', sans-serif !important; 
        }
        .stApp {
            background: radial-gradient(circle at top right, #1a233a, #0b0f19) !important;
            color: #f8fafc !important;
        }
        
        /* 標題設定 */
        .main-title { font-size: 2.2rem; font-weight: 800; color: #f8fafc; text-align: center; margin: 1rem 0; letter-spacing: 2px;}
        .sub-title { font-size: 1.1rem; color: #38bdf8; text-align: center; margin-bottom: 2rem; font-weight: 600; letter-spacing: 1px;}
        
        /* 隱藏預設頂部與側邊欄干擾 */
        header {visibility: hidden;}
        
        /* 圖表卡片設定 */
        .chart-container { 
            background: #151e2d; 
            padding: 20px; 
            border-radius: 12px; 
            box-shadow: 0 4px 20px rgba(0,0,0,0.5); 
            margin-bottom: 20px; 
            border: 1px solid #334155; 
        }
        
        /* 頁尾 */
        .footer { text-align: center; color: #64748b; font-size: 0.85rem; margin-top: 3rem; }
        
        /* Streamlit 原生 Metric 覆寫 */
        div[data-testid="metric-container"] {
            background-color: #151e2d;
            border: 1px solid #334155;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        div[data-testid="metric-container"] > div {
            color: #f8fafc !important;
        }
        div[data-testid="metric-container"] label {
            color: #94a3b8 !important;
            font-weight: 600 !important;
        }
    </style>
""", unsafe_allow_html=True)

# === 1.5 安全防禦機制 (高對比登入介面) ===
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] {display: none;}
            [data-testid="collapsedControl"] {display: none;}
            
            /* 高對比登入卡片 */
            [data-testid="stVerticalBlockBorderWrapper"] {
                background: linear-gradient(145deg, #1e293b, #0f172a) !important;
                border-radius: 16px !important;
                border: 1px solid #38bdf8 !important; /* 銳利的藍色邊框 */
                box-shadow: 0 0 30px rgba(56, 189, 248, 0.15) !important;
                padding: 30px 40px !important;
            }
            
            /* 強制覆寫輸入框樣式以適應深色模式 */
            div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
                background-color: #0b0f19 !important;
                border: 1px solid #475569 !important;
                color: #f8fafc !important;
            }
            input, select { color: #f8fafc !important; }
        </style>
        """, unsafe_allow_html=True
    )

    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1]) 
    
    with col2:
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center; color: #f8fafc; font-weight: 800; margin-bottom: 20px; letter-spacing: 1px;'>聯稽總部戰略儀表板</h2>", unsafe_allow_html=True)
            st.markdown("<hr style='border-color: #334155; margin-top: -10px; margin-bottom: 25px;'>", unsafe_allow_html=True)
            
            st.markdown("<div style='color: #38bdf8; font-size: 0.85rem; margin-bottom: 5px; font-weight: 700; letter-spacing: 1px;'>🏢 COMPANY</div>", unsafe_allow_html=True)
            st.selectbox("company", ["遠東新世紀FENC"], label_visibility="collapsed")
            
            st.markdown("<div style='color: #38bdf8; font-size: 0.85rem; margin-bottom: 5px; margin-top: 15px; font-weight: 700; letter-spacing: 1px;'>👤 ACCOUNT</div>", unsafe_allow_html=True)
            st.text_input("account", value="聯合稽核總部", disabled=True, label_visibility="collapsed")
            
            st.markdown("<div style='color: #38bdf8; font-size: 0.85rem; margin-bottom: 5px; margin-top: 15px; font-weight: 700; letter-spacing: 1px;'>🔒 PASSWORD</div>", unsafe_allow_html=True)
            pwd = st.text_input("password", type="password", label_visibility="collapsed")
            
            st.markdown("<p style='font-size: 0.8rem; color: #94a3b8; margin-top: 8px; margin-bottom: 25px;'>* 預設密碼為5碼工號。<a href='#' style='color:#38bdf8; text-decoration: none;'> Forgot Password?</a></p>", unsafe_allow_html=True)
            
            # 使用自定義的高對比按鈕
            if st.button("AUTHENTICATE 授權登入", type="primary", use_container_width=True):
                if pwd == "AUDIT@01":
                    st.session_state["password_correct"] = True
                    st.rerun()
                elif pwd != "":
                    st.error("🚫 密碼錯誤，拒絕存取。")
            
            st.markdown("<div style='font-size: 0.85rem; text-align: center; margin-top: 25px; font-weight: 500; color: #64748b;'>SYSTEM ADMIN: 李宗念 (EXT: 6855)</div>", unsafe_allow_html=True)

    return False

if not check_password():
    st.stop()


# === 2. 核心功能模組 ===
st.markdown('<div class="main-title">FAR EASTERN GROUP</div><div class="sub-title">聯合稽核總部 ｜ 戰略決策儀表板</div>', unsafe_allow_html=True)

def check_market_status(market_type='TW'):
    now = datetime.now(tw_tz)
    
    if market_type == 'CRYPTO':
        return "open", "🟢 數位資產 (24H 交易)"
        
    if market_type == 'US':
        hour = now.hour
        if 21 <= hour or hour < 5:
            return "open", "🟢 國際市場 (交易中)"
        else:
            return "closed", "🔴 國際市場 (休市/盤後)"
            
    current_time = now.time()
    market_open = dt_time(9, 0)
    market_close = dt_time(13, 35) 
    is_weekend = now.weekday() >= 5
    
    if is_weekend:
        return "closed", "🔴 台股市場 (週末休市)"
    elif market_open <= current_time <= market_close:
        return "open", "🟢 台股市場 (盤中即時)"
    else:
        return "closed", "🔴 台股市場 (盤後結算)"

@st.cache_data(ttl=3600) 
def fetch_twse_history_proxy(stock_code):
    try:
        data_list = []
        now = datetime.now()
        dates_to_fetch = []
        curr_month = now.replace(day=1)
        for i in range(6):
            target_date = curr_month - pd.DateOffset(months=i)
            dates_to_fetch.append(target_date.strftime('%Y%m01'))
            
        for date_str in dates_to_fetch:
            url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={stock_code}"
            r = requests.get(url) 
            json_data = r.json()
            
            if json_data['stat'] == 'OK':
                for row in json_data['data']:
                    date_parts = row[0].split('/')
                    ad_year = int(date_parts[0]) + 1911
                    date_iso = f"{ad_year}-{date_parts[1]}-{date_parts[2]}"
                    def to_float(s):
                        try: return float(s.replace(',', ''))
                        except: return 0.0
                    
                    vol_shares = to_float(row[1])
                    data_list.append({
                        'date': date_iso,
                        'volume': vol_shares, 
                        'open': to_float(row[3]),
                        'high': to_float(row[4]),
                        'low': to_float(row[5]),
                        'close': to_float(row[6]),
                    })
        data_list.sort(key=lambda x: x['date'])
        return data_list
    except Exception as e:
        return None

@st.cache_data(ttl=3600)
def fetch_us_history(ticker_symbol):
    try:
        tk = yf.Ticker(ticker_symbol)
        hist = tk.history(period="6mo")
        data_list = []
        for index, row in hist.iterrows():
            data_list.append({
                'date': index.strftime('%Y-%m-%d'),
                'volume': float(row['Volume']),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close'])
            })
        return data_list
    except:
        return None

@st.cache_data(ttl=300) 
def get_intraday_chart_data(stock_code, is_us_source=False):
    try:
        ticker_symbol = stock_code if is_us_source else f"{stock_code}.TW"
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="1d", interval="1m")
        if df.empty:
            df = ticker.history(period="5d", interval="5m")
            if not df.empty:
                last_day = df.index[-1].date()
                df = df[df.index.date == last_day]
        if df.empty: return None
        return df
    except:
        return None

# === 3. 繪圖模組 (全面更新為深色高對比主題) ===
def get_dark_layout(title_text):
    return dict(
        title=f"<b>{title_text}</b>",
        font=dict(color='#e2e8f0'),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(showgrid=False, gridcolor='#334155', tickfont=dict(color='#94a3b8')),
        yaxis=dict(showgrid=True, gridcolor='#1e293b', tickfont=dict(color='#94a3b8'), zerolinecolor='#334155')
    )

def plot_daily_k(df):
    if df.empty: return None
    df = df.copy()
    df['Date'] = pd.to_datetime(df['date'])
    df.set_index('Date', inplace=True)
    df = df.tail(120)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#ef4444', increasing_fillcolor='#ef4444', # 紅色上漲 (台股習慣)
        decreasing_line_color='#22c55e', decreasing_fillcolor='#22c55e', # 綠色下跌
        name="日K"
    )])
    layout = get_dark_layout("📊 歷史價格走勢 (近半年)")
    layout['xaxis_rangeslider_visible'] = False
    layout['height'] = 350
    fig.update_layout(**layout)
    return fig

def plot_intraday_line(df):
    if df is None or df.empty: return None
    interval_str = "1 Min" if (df.index[1] - df.index[0]).seconds == 60 else "5 Min"
    y_min, y_max = df['Close'].min(), df['Close'].max()
    padding = (y_max - y_min) * 0.1 if y_max != y_min else y_max * 0.01
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'], mode='lines',
        line=dict(color='#38bdf8', width=2.5), # 亮藍色線條
        fill='tozeroy', fillcolor='rgba(56, 189, 248, 0.1)', name='報價'
    ))
    fig.add_hline(y=df['Open'].iloc[0], line_dash="dot", line_color="#94a3b8", annotation_text="開盤", annotation_font_color="#94a3b8")
    
    layout = get_dark_layout(f"⚡ 當日分時動態 ({interval_str})")
    layout['height'] = 350
    layout['hovermode'] = "x unified"
    layout['yaxis']['tickformat'] = '.2f'
    layout['yaxis']['range'] = [y_min - padding, y_max + padding]
    layout['xaxis']['tickformat'] = '%H:%M'
    fig.update_layout(**layout)
    return fig

def plot_relative_strength(df_target, df_bench, target_name, bench_name):
    if df_target.empty or df_bench.empty: return None
    
    df1 = df_target[['date', 'close']].tail(60).copy()
    df2 = df_bench[['date', 'close']].tail(60).copy()
    
    merged = pd.merge(df1, df2, on='date', suffixes=('_target', '_bench'), how='inner')
    if merged.empty: return None
    
    base_target = merged['close_target'].iloc[0]
    base_bench = merged['close_bench'].iloc[0]
    merged['Target_Norm'] = (merged['close_target'] / base_target) * 100
    merged['Bench_Norm'] = (merged['close_bench'] / base_bench) * 100
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=merged['date'], y=merged['Bench_Norm'], mode='lines',
        line=dict(color='#64748b', width=2, dash='dash'), name=bench_name
    ))
    fig.add_trace(go.Scatter(
        x=merged['date'], y=merged['Target_Norm'], mode='lines',
        line=dict(color='#facc15', width=3), name=target_name # 金色強調線條
    ))
    
    layout = get_dark_layout(f"🛡️ 戰略雷達：相對強勢分析 (對標 {bench_name})")
    layout['height'] = 350
    layout['hovermode'] = "x unified"
    layout['yaxis']['title'] = "累積報酬指數 (Base=100)"
    fig.update_layout(**layout)
    return fig

# === 4. 主控台邏輯 ===
market_categories = {
    "📈 總體經濟與大盤 (宏觀與風險指標)": {
        "🇹🇼 台灣加權指數 (TAIEX)": "^TWII",
        "🇺🇸 S&P 500 (標普 500 指數)": "^GSPC",
        "🇺🇸 Dow Jones (道瓊工業指數)": "^DJI",
        "🇺🇸 Nasdaq (那斯達克指數)": "^IXIC",
        "🇺🇸 SOX (費城半導體指數)": "^SOX",
        "⚠️ VIX 恐慌指數 (市場風險)": "^VIX",
        "🏦 U.S. 10Y Treasury (實質利率)": "^TNX",
        "🥇 黃金期貨 (資金避險)": "GC=F",
        "🥈 白銀期貨 (工業金屬)": "SI=F",
        "🛢️ WTI 原油 (能源成本)": "CL=F",
        "₿ 比特幣 (數位資產)": "BTC-USD",
        "💵 美元指數 (DXY)": "DX-Y.NYB",
        "💱 美元兌台幣 (匯率曝險)": "TWD=X",
        "☁️ 棉花期貨 (紡纖原物料)": "CT=F",
        "🚢 BDRY 散裝航運 ETF (運價指標)": "BDRY"
    },
    "🏢 遠東集團核心事業體": {
        "🇹🇼 1402 遠東新": "1402", 
        "🇹🇼 1102 亞泥": "1102", 
        "🇹🇼 2606 裕民": "2606",
        "🇹🇼 1460 宏遠": "1460", 
        "🇹🇼 2903 遠百": "2903", 
        "🇹🇼 4904 遠傳": "4904", 
        "🇹🇼 1710 東聯": "1710"
    },
    "👕 國際品牌終端 (紡織板塊對標)": {
        "🇺🇸 Nike": "NKE",
        "🇺🇸 Under Armour": "UAA",
        "🇺🇸 Lululemon": "LULU",
        "🇺🇸 Adidas (ADR)": "ADDYY",
        "🇺🇸 Puma (ADR)": "PUMSY",
        "🇺🇸 Columbia": "COLM",
        "🇺🇸 Gap Inc": "GAP",
        "🇺🇸 Fast Retailing (Uniqlo ADR)": "FRCOY",
        "🇺🇸 VF Corp": "VFC"
    },
    "🥤 國際品牌終端 (化纖板塊對標)": {
        "🇺🇸 Coca-Cola": "KO",
        "🇺🇸 PepsiCo": "PEP"
    }
}

with st.sidebar:
    st.markdown("<h2 style='color:#f8fafc;'>🎯 戰略監控目標</h2>", unsafe_allow_html=True)
    selected_category = st.selectbox("板塊分類", list(market_categories.keys()))
    st.markdown("<hr style='border-color: #334155;'>", unsafe_allow_html=True)
    
    options_dict = market_categories[selected_category]
    option = st.radio("監控標的", list(options_dict.keys()))
    code = options_dict[option]
    
    is_tw_stock = code.isdigit()
    is_tw_index = (code == "^TWII")
    is_us_index = (code in ["^GSPC", "^DJI", "^IXIC", "^SOX", "^VIX", "^TNX"])
    is_crypto = ("BTC" in code)
    is_forex = ("=X" in code or "DX" in code)
    is_futures = ("=F" in code)
    
    is_us_stock = not (is_tw_stock or is_tw_index or is_us_index or is_crypto or is_forex or is_futures)
    
    if is_tw_stock or is_tw_index or code == "TWD=X": market_type = 'TW'
    elif is_crypto: market_type = 'CRYPTO'
    else: market_type = 'US'
    
    st.divider()
    status_code, status_text = check_market_status(market_type=market_type)
    st.info(f"系統狀態：{status_text}")
    if is_us_stock and len(code) > 4: st.caption("註：本標的為 ADR，走勢具母國連動性。")
    if st.button("🔄 強制同步最新報價", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# === 5. 資料處理 ===
real_data = {'price': 0, 'high': '-', 'low': '-', 'open': '-', 'volume': '-'}

if is_tw_stock:
    try:
        real = twstock.realtime.get(code)
        if real['success']:
            info = real['realtime']
            latest = float(info['latest_trade_price']) if info['latest_trade_price'] != '-' else 0.0
            if latest == 0.0: latest = float(info['open']) if info['open'] != '-' else 0.0
            real_data['price'] = latest
            real_data['high'] = info.get('high', '-')
            real_data['low'] = info.get('low', '-')
            real_data['open'] = info.get('open', '-')
            real_data['volume'] = info.get('accumulate_trade_volume', '0') 
    except: pass
    hist_data = fetch_twse_history_proxy(code)
else:
    try:
        tk = yf.Ticker(code)
        fi = tk.fast_info
        latest = fi.last_price
        real_data['price'] = latest
        real_data['open'] = fi.open
        real_data['high'] = fi.day_high
        real_data['low'] = fi.day_low
        real_data['volume'] = f"{int(fi.last_volume):,}"
    except: pass
    hist_data = fetch_us_history(code)

df_daily = pd.DataFrame(hist_data) if hist_data else pd.DataFrame()
df_intra = get_intraday_chart_data(code, is_us_source=not is_tw_stock)

df_bench = pd.DataFrame()
bench_name = ""
if not df_daily.empty:
    if is_tw_stock:
        bench_code, bench_name = "^TWII", "TAIEX (台灣加權指數)"
    elif code == "^TWII" or is_us_stock or code in ["^DJI", "^IXIC", "^SOX"]:
        bench_code, bench_name = "^GSPC", "S&P 500 指數"
    elif code == "^GSPC":
        bench_code, bench_name = "^TWII", "TAIEX (台灣加權指數)"
    else:
        bench_code, bench_name = "^GSPC", "S&P 500 指數"
        
    if bench_code != code:
        bench_hist = fetch_us_history(bench_code)
        if bench_hist: df_bench = pd.DataFrame(bench_hist)

current_price = real_data['price']
if (current_price == 0 or current_price is None) and not df_daily.empty:
    current_price = df_daily.iloc[-1]['close']
    real_data['high'] = df_daily.iloc[-1]['high']
    real_data['low'] = df_daily.iloc[-1]['low']
    real_data['open'] = df_daily.iloc[-1]['open']
    vol_num = df_daily.iloc[-1]['volume']
    real_data['volume'] = f"{int(vol_num / 1000):,}" if is_tw_stock else f"{int(vol_num):,}"

prev_close = 0
if not df_daily.empty:
    if not is_tw_stock: 
        try: prev_close = tk.fast_info.previous_close
        except: prev_close = df_daily.iloc[-2]['close'] if len(df_daily) > 1 else df_daily.iloc[-1]['close']
    else: 
        last_date = df_daily.iloc[-1]['date']
        today_str = datetime.now().strftime('%Y-%m-%d')
        prev_close = df_daily.iloc[-2]['close'] if last_date == today_str and len(df_daily) > 1 else df_daily.iloc[-1]['close']

change = current_price - prev_close
pct = (change / prev_close) * 100 if prev_close != 0 else 0

# === 6. UI 呈現 (高對比戰略面板) ===
bg_color = "#151e2d"
font_color = "#ef4444" if change >= 0 else "#22c55e" # 螢光紅(漲), 螢光綠(跌)
border_color = "#ef4444" if change >= 0 else "#22c55e"

currency_symbol = "NT$" if (is_tw_stock or is_tw_index or code == "TWD=X") else "$"
unit_label = "Pts" if (is_tw_index or is_us_index or code == "DX-Y.NYB") else \
             "/ oz" if (is_futures and ("GC" in code or "SI" in code)) else \
             "/ bbl" if (is_futures and "CL" in code) else \
             "%" if code == "^TNX" else ""

# A. 核心報價卡片
st.markdown(f"""
<div style="background-color: {bg_color}; padding: 30px; border-radius: 12px; margin-bottom: 25px; border-left: 8px solid {border_color}; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
    <h2 style="margin:0; color:#94a3b8; font-size: 1.2rem; font-weight: 700; letter-spacing: 1px;">{option}</h2>
    <div style="display: flex; align-items: baseline; gap: 20px; margin-top: 12px;">
        <span style="font-size: 3.5rem; font-weight: 800; color: #f8fafc; letter-spacing: -1px; text-shadow: 0 2px 10px rgba(255,255,255,0.1);">
           {currency_symbol.replace('NT$', '') if code != '^TNX' else ''} {current_price:,.2f} <span style="font-size: 1.2rem; color:#64748b; font-weight: 500;">{unit_label}</span>
        </span>
        <span style="font-size: 1.8rem; font-weight: 700; color: {font_color};">
             {change:+.2f} ({pct:+.2f}%)
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# B. 市場深度指標
hide_volume = (is_tw_index or is_us_index or is_forex)
safe_fmt = lambda x: f"{x:,.2f}" if isinstance(x, (int, float)) else x

if hide_volume:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("OPEN 開盤價", safe_fmt(real_data.get('open')))
    c2.metric("HIGH 最高價", safe_fmt(real_data.get('high')))
    c3.metric("LOW 最低價", safe_fmt(real_data.get('low')))
    c4.metric("PREV CLOSE 前日收盤", f"{prev_close:,.2f}")
else:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("OPEN 開盤價", safe_fmt(real_data.get('open')))
    c2.metric("HIGH 最高價", safe_fmt(real_data.get('high')))
    c3.metric("LOW 最低價", safe_fmt(real_data.get('low')))
    c4.metric("PREV CLOSE 前日收盤", f"{prev_close:,.2f}")
    vol_label = "VOLUME 成交量(張)" if is_tw_stock else "VOLUME 成交量"
    c5.metric(vol_label, real_data.get('volume', '-'))

st.divider()

# C. 數據視覺化圖表
col1, col2 = st.columns([1, 1])
with col1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    if df_intra is not None and not df_intra.empty:
        st.plotly_chart(plot_intraday_line(df_intra), use_container_width=True)
    else:
        st.warning("暫無分時資料 (市場休市或限流)")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    if not df_daily.empty:
        st.plotly_chart(plot_daily_k(df_daily), use_container_width=True)
    else:
        st.error("暫無歷史交易資料 (可能因資料源尚未收錄此板塊指數)")
    st.markdown('</div>', unsafe_allow_html=True)

# D. 戰略雷達：相對強勢
if not df_bench.empty and not df_daily.empty:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    rs_fig = plot_relative_strength(df_daily, df_bench, option.split(" ")[-1], bench_name)
    if rs_fig:
        st.plotly_chart(rs_fig, use_container_width=True)
        st.caption("🔍 **戰略註記**：將雙邊起漲點設為 100 基準化。當資產曲線（金）凌駕於大盤曲線（灰）之上，表彰該標的具備超越大環境之動能（Alpha）。")
    st.markdown('</div>', unsafe_allow_html=True)

# === 7. 高階幕僚戰略解讀 ===
# (字典內容保持不變，為節省篇幅此處省略字典宣告，你原本的 strategic_commentary 字典維持即可)
strategic_commentary = {
    # ... (請保留你原有的 strategic_commentary 字典內容) ...
    "^TWII": {
        "title": "🇹🇼 台灣加權指數 (TAIEX)",
        "business_model": "反映台灣整體資本市場動能與外資流向，為評估集團旗下台股掛牌企業（如遠東新、亞泥）之系統性估值基準。",
        "high": "🟢 【資金行情熱絡】大盤屢創新高，代表市場資金充沛。有利於集團旗下資產股之重估（Revaluation）與資本市場籌資行動。",
        "low": "🔴 【系統性回檔】市場整體本益比（PE）下修。防禦型與高殖利率標的（如亞泥、遠傳）將發揮避險與資金避風港之戰略作用。"
    },
    "^VIX": {
        "title": "⚠️ VIX 恐慌指數 (市場波動率指標)",
        "business_model": "衡量總體經濟避險情緒與流動性壓力的關鍵指標，直接關聯集團資本運作的外部環境風險。",
        "high": "🔴 【風險溢酬升溫】代表市場流動性趨緊。建議啟動防禦機制，暫緩非必要之資本支出（CapEx），並重新檢視短期債務延展風險。",
        "low": "🟢 【市場情緒穩定】資金承擔風險意願高。有利於集團旗下事業體向金融機構取得具競爭力之長期融資，為戰略佈局之契機。"
    }
    # ... 其他標的 ...
}

if code in strategic_commentary:
    st.markdown("<h3 style='color: #f8fafc; font-weight: 700; margin-top: 20px;'>📊 戰略洞察 (Tactical Insights)</h3>", unsafe_allow_html=True)
    info = strategic_commentary[code]
    
    # 戰略解讀卡片深色化
    st.markdown(f"""
    <div style="background-color: #151e2d; padding: 25px; border-radius: 12px; border-left: 5px solid #38bdf8; margin-bottom: 20px; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155;">
        <h4 style="margin-top: 0; color: #f8fafc; font-size: 1.2rem; border-bottom: 1px solid #334155; padding-bottom: 12px; font-weight: 700;">{info['title']}</h4>
        <p style="color: #cbd5e1; font-size: 1rem; margin-top: 15px; line-height: 1.7;"><strong>核心業務關聯：</strong>{info['business_model']}</p>
        <div style="display: flex; gap: 20px; margin-top: 20px;">
            <div style="flex: 1; background: rgba(239, 68, 68, 0.1); padding: 20px; border-radius: 8px; border: 1px solid rgba(239, 68, 68, 0.3);">
                <p style="margin: 0; font-size: 0.95rem; color: #fca5a5; line-height: 1.6; font-weight: 500;">{info['high']}</p>
            </div>
            <div style="flex: 1; background: rgba(34, 197, 94, 0.1); padding: 20px; border-radius: 8px; border: 1px solid rgba(34, 197, 94, 0.3);">
                <p style="margin: 0; font-size: 0.95rem; color: #86efac; line-height: 1.6; font-weight: 500;">{info['low']}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f'<div class="footer">SYSTEM LAST UPDATED：{update_time} ｜ DATA SOURCE：TWSE, Yahoo Finance</div>', unsafe_allow_html=True)
