import streamlit as st
import twstock
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, time as dt_time
import pytz
import requests
import urllib3
import yfinance as yf

# === 0. 系統層級修復 ===
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
original_request = requests.Session.request
def patched_request(self, method, url, *args, **kwargs):
    kwargs['verify'] = False
    return original_request(self, method, url, *args, **kwargs)
requests.Session.request = patched_request

# === 1. 戰情室初始化 ===
st.set_page_config(page_title="遠東集團_戰情室", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei') 

# CSS 美化
st.markdown("""
    <style>
        html, body, [class*="css"]  { font-family: 'Microsoft JhengHei', sans-serif !important; }
        .main-title { font-size: 2.5rem; font-weight: 700; color: #1d1d1f; text-align: center; margin: 1rem 0; }
        .chart-container { background: white; padding: 15px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .footer { text-align: center; color: #888; font-size: 0.8rem; margin-top: 3rem; }
        /* 指標卡片樣式 */
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

def check_market_status():
    now = datetime.now(tw_tz)
    current_time = now.time()
    market_open = dt_time(9, 0)
    market_close = dt_time(13, 35) 
    is_weekend = now.weekday() >= 5
    
    if is_weekend:
        return "closed", "🌙 休市 (週末)"
    elif market_open <= current_time <= market_close:
        return "open", "🟢 盤中 (即時連線)"
    else:
        return "closed", "🌙 盤後 (日結資料)"

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
                    
                    # row[1] 是成交股數 (Volume in shares)
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

@st.cache_data(ttl=300) 
def get_intraday_chart_data(stock_code):
    try:
        ticker = yf.Ticker(f"{stock_code}.TW")
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

# === 3. 繪圖模組 (關鍵修改：動態 Y 軸) ===

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
    
    # 判斷時間頻率
    interval_str = "1分K" if (df.index[1] - df.index[0]).seconds == 60 else "5分K"
    
    # [關鍵修正] 計算 Y 軸範圍，讓波動看起來更明顯
    y_min = df['Close'].min()
    y_max = df['Close'].max()
    # 上下各留 10% 緩衝空間，避免線貼著邊框
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
        # 強制設定 Y 軸範圍，達成「放大鏡」效果
        yaxis=dict(showgrid=True, gridcolor='#eee', tickformat='.2f', range=y_range) 
    )
    return fig

# === 4. 主控台邏輯 ===
stock_map = {
    "1402 遠東新": "1402", "1102 亞泥": "1102", "2606 裕民": "2606",
    "1460 宏遠": "1460", "2903 遠百": "2903", "4904 遠傳": "4904", "1710 東聯": "1710"
}

with st.sidebar:
    st.header("🎯 監控目標")
    option = st.radio("選擇公司", list(stock_map.keys()))
    code = stock_map[option]
    st.divider()
    status_code, status_text = check_market_status()
    st.info(f"狀態：{status_text}")
    if st.button("🔄 刷新情報"):
        st.cache_data.clear()
        st.rerun()

# === 5. 資料處理 ===
real_data = {}
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
        # 證交所即時 API 的 accumulate_trade_volume 通常是 "張數" (Lots)
        real_data['volume'] = info.get('accumulate_trade_volume', '0') 
    else:
        real_data['price'] = 0
except:
    real_data['price'] = 0

hist_data = fetch_twse_history_proxy(code)
df_daily = pd.DataFrame(hist_data) if hist_data else pd.DataFrame()

# 獲取當日走勢
df_intra = get_intraday_chart_data(code)

# 數據整合 (Fallback 機制)
current_price = real_data['price']
if current_price == 0 and not df_daily.empty:
    current_price = df_daily.iloc[-1]['close']
    real_data['high'] = df_daily.iloc[-1]['high']
    real_data['low'] = df_daily.iloc[-1]['low']
    real_data['open'] = df_daily.iloc[-1]['open']
    # 歷史資料的 volume 是股數，要除以 1000 變張數
    real_data['volume'] = f"{int(df_daily.iloc[-1]['volume'] / 1000):,}"

prev_close = 0
if not df_daily.empty:
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

# A. 大張價格卡片
st.markdown(f"""
<div style="background-color: {bg_color}; padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 1px solid rgba(0,0,0,0.05);">
    <h2 style="margin:0; color:#555; font-size: 1.2rem;">{option}</h2>
    <div style="display: flex; align-items: baseline; gap: 15px; margin-top: 5px;">
        <span style="font-size: 3.8rem; font-weight: 800; color: #1d1d1f; letter-spacing: -1px;">{current_price}</span>
        <span style="font-size: 1.6rem; font-weight: 600; color: {font_color};">
            {change:+.2f} ({pct:+.2f}%)
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# B. 關鍵指標列 (新增：開盤、成交量)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("開盤價", real_data.get('open', '-'))
c2.metric("最高價", real_data.get('high', '-'))
c3.metric("最低價", real_data.get('low', '-'))
c4.metric("昨收價", prev_close)
# 成交量顯示處理
vol_str = str(real_data.get('volume', '-'))
c5.metric("成交量 (張)", vol_str)

st.divider()

# C. 圖表區
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    if df_intra is not None and not df_intra.empty:
        st.plotly_chart(plot_intraday_line(df_intra), use_container_width=True)
    else:
        st.warning("⚠️ 無法取得即時分時圖")
        st.caption("可能原因：盤前試搓中、或 Yahoo API 短暫限流")
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
