import streamlit as st
import twstock
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, time as dt_time
import pytz
import requests
import urllib3
import yfinance as yf

# === 0. 系統層級修復 (解決部分公司網域 SSL 問題) ===
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
original_request = requests.Session.request
def patched_request(self, method, url, *args, **kwargs):
    kwargs['verify'] = False
    return original_request(self, method, url, *args, **kwargs)
requests.Session.request = patched_request

# === 1. 戰情室初始化 ===
st.set_page_config(page_title="遠東集團_戰情室", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei') 

# CSS 美化設定
st.markdown("""
    <style>
        html, body, [class*="css"]  { font-family: 'Microsoft JhengHei', sans-serif !important; }
        .main-title { font-size: 2.5rem; font-weight: 700; color: #1d1d1f; text-align: center; margin: 1rem 0; }
        .chart-container { background: white; padding: 15px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .footer { text-align: center; color: #888; font-size: 0.8rem; margin-top: 3rem; }
        div[data-testid="metric-container"] {
            background-color: #f8f9fa;
            border: 1px solid #eee;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">遠東集團<br>聯合稽核總部 一處戰情室</div>', unsafe_allow_html=True)

# === 2. 核心功能模組 ===

def check_market_status(is_us_stock=False):
    now = datetime.now(tw_tz)
    
    if is_us_stock:
        # 美股簡易判斷 (夏令時間未精細處理，僅作概略提示)
        # 美股通常為台灣時間 21:30/22:30 開盤，隔日 04:00/05:00 收盤
        hour = now.hour
        if 21 <= hour or hour < 5:
            return "open", "🇺🇸 美股開盤中"
        else:
            return "closed", "🇺🇸 美股休市 (盤後)"
            
    current_time = now.time()
    market_open = dt_time(9, 0)
    market_close = dt_time(13, 35) 
    is_weekend = now.weekday() >= 5
    
    if is_weekend:
        return "closed", "🌙 台股休市 (週末)"
    elif market_open <= current_time <= market_close:
        return "open", "🟢 台股盤中 (即時連線)"
    else:
        return "closed", "🌙 台股盤後 (日結資料)"

@st.cache_data(ttl=3600) 
def fetch_twse_history_proxy(stock_code):
    try:
        data_list = []
        now = datetime.now()
        dates_to_fetch = [now.strftime('%Y%m01')]
        first_day_this_month = now.replace(day=1)
        last_month = first_day_this_month - timedelta(days=1)
        dates_to_fetch.insert(0, last_month.strftime('%Y%m01'))
        
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
        return data_list
    except Exception as e:
        return None

@st.cache_data(ttl=3600)
def fetch_us_history(ticker_symbol):
    try:
        tk = yf.Ticker(ticker_symbol)
        hist = tk.history(period="3mo")
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
def get_intraday_chart_data(stock_code, is_us=False):
    try:
        ticker_symbol = stock_code if is_us else f"{stock_code}.TW"
        ticker = yf.Ticker(ticker_symbol)
        
        df = ticker.history(period="1d", interval="1m")
        if df.empty:
            df = ticker.history(period="5d", interval="5m")
            if not df.empty:
                last_day = df.index[-1].date()
                df = df[df.index.date == last_day]
        
        if df.empty:
            return None
        return df
    except:
        return None

# === 3. 繪圖模組 ===

def plot_daily_k(df):
    if df.empty: return None
    df['Date'] = pd.to_datetime(df['date'])
    df.set_index('Date', inplace=True)
    df = df.tail(60)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#ef4444', increasing_fillcolor='#ef4444',
        decreasing_line_color='#22c55e', decreasing_fillcolor='#22c55e',
        name="日K"
    )])
    fig.update_layout(
        title="<b>📅 近兩個月日線走勢 (Trend)</b>",
        xaxis_rangeslider_visible=False,
        height=350,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#eee')
    )
    return fig

def plot_intraday_line(df):
    if df is None or df.empty: return None
    
    interval_str = "1分K" if (df.index[1] - df.index[0]).seconds == 60 else "5分K"
    
    y_min = df['Close'].min()
    y_max = df['Close'].max()
    padding = (y_max - y_min) * 0.1 if y_max != y_min else y_max * 0.01
    y_range = [y_min - padding, y_max + padding]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'],
        mode='lines',
        line=dict(color='#007AFF', width=2),
        fill='tozeroy',
        fillcolor='rgba(0, 122, 255, 0.1)',
        name='股價'
    ))
    
    ref_price = df['Open'].iloc[0]
    fig.add_hline(y=ref_price, line_dash="dot", line_color="gray", annotation_text="開盤")
    
    fig.update_layout(
        title=f"<b>⚡ 本日即時/盤後走勢 ({interval_str})</b>",
        height=300,
        margin=dict(l=10, r=10, t=40, b=10),
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(tickformat='%H:%M', showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#eee', tickformat='.2f', range=y_range) 
    )
    return fig

# === 4. 主控台邏輯 (完整擴充版) ===
stock_map = {
    # --- 🇹🇼 遠東集團軍 (台股) ---
    "🇹🇼 1402 遠東新": "1402", 
    "🇹🇼 1102 亞泥": "1102", 
    "🇹🇼 2606 裕民": "2606",
    "🇹🇼 1460 宏遠": "1460", 
    "🇹🇼 2903 遠百": "2903", 
    "🇹🇼 4904 遠傳": "4904", 
    "🇹🇼 1710 東聯": "1710",
    
    # --- 🇺🇸 運動品牌客戶 (美股/ADR) ---
    "🇺🇸 Nike (耐吉)": "NKE",
    "🇺🇸 Under Armour (UA)": "UAA",
    "🇺🇸 Lululemon (露露檸檬)": "LULU",
    "🇺🇸 Adidas (愛迪達 ADR)": "ADDYY",
    "🇺🇸 Puma (彪馬 ADR)": "PUMSY",
    "🇺🇸 Columbia (哥倫比亞)": "COLM",
    
    # --- 🇺🇸 休閒與快時尚客戶 (美股/ADR) ---
    "🇺🇸 Gap Inc (蓋璞)": "GAP",
    "🇺🇸 Fast Retailing (Uniqlo ADR)": "FRCOY",
    "🇺🇸 VF Corp (Vans/North Face)": "VFC",
    
    # --- 🇺🇸 飲料食品客戶 ---
    "🇺🇸 Coca-Cola (可口可樂)": "KO",
    "🇺🇸 PepsiCo (百事)": "PEP"
}

with st.sidebar:
    st.header("🎯 監控目標")
    option = st.radio("選擇公司", list(stock_map.keys()))
    code = stock_map[option]
    
    # 自動判斷：代號不是純數字 = 美股/ADR
    is_us = not code.isdigit()
    
    st.divider()
    status_code, status_text = check_market_status(is_us_stock=is_us)
    st.info(f"狀態：{status_text}")
    
    if is_us and len(code) > 4:
         st.caption("ℹ️ 此為 ADR (存託憑證)，走勢與母國連動，以美元計價。")
         
    if st.button("🔄 刷新情報"):
        st.cache_data.clear()
        st.rerun()

# === 5. 資料處理 ===
real_data = {'price': 0, 'high': '-', 'low': '-', 'open': '-', 'volume': '-'}

if not is_us:
    # --- 台股處理邏輯 ---
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
    except:
        pass
    
    hist_data = fetch_twse_history_proxy(code)

else:
    # --- 美股處理邏輯 ---
    try:
        tk = yf.Ticker(code)
        fi = tk.fast_info
        
        latest = fi.last_price
        
        real_data['price'] = latest
        real_data['open'] = fi.open
        real_data['high'] = fi.day_high
        real_data['low'] = fi.day_low
        real_data['volume'] = f"{int(fi.last_volume):,}"
    except:
        pass
    
    hist_data = fetch_us_history(code)

# 共用邏輯
df_daily = pd.DataFrame(hist_data) if hist_data else pd.DataFrame()
df_intra = get_intraday_chart_data(code, is_us=is_us)

current_price = real_data['price']

# Fallback 機制
if (current_price == 0 or current_price is None) and not df_daily.empty:
    current_price = df_daily.iloc[-1]['close']
    real_data['high'] = df_daily.iloc[-1]['high']
    real_data['low'] = df_daily.iloc[-1]['low']
    real_data['open'] = df_daily.iloc[-1]['open']
    
    vol_num = df_daily.iloc[-1]['volume']
    if not is_us:
        real_data['volume'] = f"{int(vol_num / 1000):,}"
    else:
        real_data['volume'] = f"{int(vol_num):,}"

# 計算漲跌
prev_close = 0
if not df_daily.empty:
    if is_us:
        try:
            prev_close = tk.fast_info.previous_close
        except:
            if len(df_daily) > 1:
                prev_close = df_daily.iloc[-2]['close']
            else:
                prev_close = df_daily.iloc[-1]['close']
    else:
        last_date = df_daily.iloc[-1]['date']
        today_str = datetime.now().strftime('%Y-%m-%d')
        if last_date == today_str and len(df_daily) > 1:
            prev_close = df_daily.iloc[-2]['close']
        else:
            prev_close = df_daily.iloc[-1]['close']

change = current_price - prev_close
pct = (change / prev_close) * 100 if prev_close != 0 else 0

# === 6. UI 呈現 ===
bg_color = "#e6fffa" if change >= 0 else "#fff5f5"
font_color = "#d0021b" if change >= 0 else "#009944"
currency_symbol = "$" if is_us else "NT$"
vol_label = "成交量 (股)" if is_us else "成交量 (張)"

# A. 價格卡片
st.markdown(f"""
<div style="background-color: {bg_color}; padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 1px solid rgba(0,0,0,0.05);">
    <h2 style="margin:0; color:#555; font-size: 1.2rem;">{option}</h2>
    <div style="display: flex; align-items: baseline; gap: 15px; margin-top: 5px;">
        <span style="font-size: 3.8rem; font-weight: 800; color: #1d1d1f; letter-spacing: -1px;">{currency_symbol} {current_price:,.2f}</span>
        <span style="font-size: 1.6rem; font-weight: 600; color: {font_color};">
            {change:+.2f} ({pct:+.2f}%)
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# B. 指標列
c1, c2, c3, c4, c5 = st.columns(5)
safe_fmt = lambda x: f"{x:,.2f}" if isinstance(x, (int, float)) else x
c1.metric("開盤價", safe_fmt(real_data.get('open')))
c2.metric("最高價", safe_fmt(real_data.get('high')))
c3.metric("最低價", safe_fmt(real_data.get('low')))
c4.metric("昨收價", f"{prev_close:,.2f}")
c5.metric(vol_label, real_data.get('volume', '-'))

st.divider()

# C. 圖表
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    if df_intra is not None and not df_intra.empty:
        st.plotly_chart(plot_intraday_line(df_intra), use_container_width=True)
    else:
        st.warning("⚠️ 無法取得即時分時圖")
        st.caption("可能原因：盤前/盤後、或資料源限流")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    if not df_daily.empty:
        st.plotly_chart(plot_daily_k(df_daily), use_container_width=True)
    else:
        st.error("無法取得歷史 K 線資料")
    st.markdown('</div>', unsafe_allow_html=True)

update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f'<div class="footer">更新時間：{update_time}</div>', unsafe_allow_html=True)
