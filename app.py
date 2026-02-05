import streamlit as st
import twstock
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, time as dt_time
import pytz
import requests
import urllib3
import yfinance as yf # 重新引入 yfinance 用於畫分時圖

# === 0. 系統層級修復 ===
# SSL 憑證補丁 (強制過證交所安檢)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
original_request = requests.Session.request
def patched_request(self, method, url, *args, **kwargs):
    kwargs['verify'] = False
    return original_request(self, method, url, *args, **kwargs)
requests.Session.request = patched_request

# === 1. 戰情室初始化 ===
st.set_page_config(page_title="遠東集團_戰情室", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei') 

# CSS 美化 (Apple 風格)
st.markdown("""
    <style>
        html, body, [class*="css"]  { font-family: 'Microsoft JhengHei', sans-serif !important; }
        .main-title { font-size: 2.5rem; font-weight: 700; color: #1d1d1f; text-align: center; margin: 1rem 0; }
        .chart-container { background: white; padding: 15px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .footer { text-align: center; color: #888; font-size: 0.8rem; margin-top: 3rem; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">遠東集團<br>聯合稽核總部 一處戰情室</div>', unsafe_allow_html=True)

# === 2. 核心功能模組 ===

# 判斷市場狀態
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

# [升級版] 抓取歷史資料 (自動跨月，確保數據足夠)
@st.cache_data(ttl=3600) # 歷史資料快取 1 小時
def fetch_twse_history_proxy(stock_code):
    try:
        data_list = []
        
        # 抓取 "本月" 和 "上個月" 的資料，確保 K 線圖夠長
        now = datetime.now()
        dates_to_fetch = [now.strftime('%Y%m01')] # 本月
        
        # 計算上個月
        first_day_this_month = now.replace(day=1)
        last_month = first_day_this_month - timedelta(days=1)
        dates_to_fetch.insert(0, last_month.strftime('%Y%m01')) # 插入上個月到最前面
        
        for date_str in dates_to_fetch:
            url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={stock_code}"
            r = requests.get(url) # SSL patch 會自動生效
            json_data = r.json()
            
            if json_data['stat'] == 'OK':
                for row in json_data['data']:
                    # 民國轉西元
                    date_parts = row[0].split('/')
                    ad_year = int(date_parts[0]) + 1911
                    date_iso = f"{ad_year}-{date_parts[1]}-{date_parts[2]}"
                    
                    def to_float(s):
                        try:
                            return float(s.replace(',', ''))
                        except:
                            return 0.0
                    
                    data_list.append({
                        'date': date_iso,
                        'open': to_float(row[3]),
                        'high': to_float(row[4]),
                        'low': to_float(row[5]),
                        'close': to_float(row[6]),
                    })
        
        return data_list
    except Exception as e:
        return None

# [新增功能] 抓取當日分時走勢 (Intraday)
@st.cache_data(ttl=300) # 關鍵：快取 5 分鐘，避免被 Yahoo 封鎖
def get_intraday_chart_data(stock_code):
    try:
        # yfinance 需要加上 .TW
        ticker = yf.Ticker(f"{stock_code}.TW")
        # 抓取當天 1 分鐘線
        df = ticker.history(period="1d", interval="1m")
        if df.empty:
            return None
        return df
    except:
        return None

# === 3. 繪圖模組 ===

# 繪製 K 線圖 (日線)
def plot_daily_k(df):
    if df.empty: return None
    df['Date'] = pd.to_datetime(df['date'])
    df.set_index('Date', inplace=True)
    
    # 只取最近 60 天，避免圖表太擠
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

# 繪製分時圖 (即時)
def plot_intraday_line(df):
    if df is None or df.empty: return None
    
    # 轉換 index 為台灣時間 (如果 yfinance 給的是 UTC)
    # yfinance history 已經是當地的 timezone usually
    
    fig = go.Figure()
    
    # 價格線
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'],
        mode='lines',
        line=dict(color='#007AFF', width=2),
        fill='tozeroy', # 填滿下方顏色，更有質感
        fillcolor='rgba(0, 122, 255, 0.1)',
        name='股價'
    ))
    
    # 抓取昨收 (用第一筆 Open 當作參考，或 yfinance info)
    ref_price = df['Open'].iloc[0]
    
    fig.add_hline(y=ref_price, line_dash="dot", line_color="gray", annotation_text="開盤參考")
    
    fig.update_layout(
        title="<b>⚡ 當日即時走勢 (Intraday)</b>",
        height=300,
        margin=dict(l=10, r=10, t=40, b=10),
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            tickformat='%H:%M',
            showgrid=False
        ),
        yaxis=dict(
            showgrid=True, 
            gridcolor='#eee',
            tickformat='.2f'
        )
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

# === 5. 資料處理與顯示 ===
# 1. 抓取主要價格 (twstock Realtime)
real_data = {}
try:
    real = twstock.realtime.get(code)
    if real['success']:
        info = real['realtime']
        latest = float(info['latest_trade_price']) if info['latest_trade_price'] != '-' else 0.0
        if latest == 0.0: latest = float(info['open']) if info['open'] != '-' else 0.0
        
        real_data['price'] = latest
        real_data['high'] = info['high']
        real_data['low'] = info['low']
else:
    real_data['price'] = 0

# 2. 抓取歷史資料 (Proxy) - 用來算昨收和畫日K
hist_data = fetch_twse_history_proxy(code)
df_daily = pd.DataFrame(hist_data) if hist_data else pd.DataFrame()

# 3. 抓取即時分時資料 (Yfinance)
df_intra = get_intraday_chart_data(code)

# 計算數據
current_price = real_data['price']
# 如果即時抓不到 (例如盤後很久)，就用歷史資料最新一筆
if current_price == 0 and not df_daily.empty:
    current_price = df_daily.iloc[-1]['close']

# 昨收與漲跌
prev_close = 0
if not df_daily.empty:
    # 如果歷史資料包含今天，那倒數第二筆才是昨收
    # 簡單判斷：看最後一筆日期是否等於今天
    last_date = df_daily.iloc[-1]['date']
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    if last_date == today_str and len(df_daily) > 1:
        prev_close = df_daily.iloc[-2]['close']
    else:
        prev_close = df_daily.iloc[-1]['close'] # 若今天資料還沒進歷史庫

change = current_price - prev_close
pct = (change / prev_close) * 100 if prev_close != 0 else 0

# === 6. UI 呈現 ===
bg_color = "#e6fffa" if change >= 0 else "#fff5f5"
font_color = "#d0021b" if change >= 0 else "#009944"

# 頂部價格卡片
st.markdown(f"""
<div style="background-color: {bg_color}; padding: 20px; border-radius: 12px; margin-bottom: 25px; border: 1px solid rgba(0,0,0,0.05);">
    <h2 style="margin:0; color:#555; font-size: 1.2rem;">{option}</h2>
    <div style="display: flex; align-items: baseline; gap: 15px; margin-top: 5px;">
        <span style="font-size: 3.8rem; font-weight: 800; color: #1d1d1f; letter-spacing: -1px;">{current_price}</span>
        <span style="font-size: 1.6rem; font-weight: 600; color: {font_color};">
            {change:+.2f} ({pct:+.2f}%)
        </span>
    </div>
    <div style="color: #666; font-size: 0.9rem; margin-top: 5px;">
        參考昨收: {prev_close} | 最高: {real_data.get('high', '-')} | 最低: {real_data.get('low', '-')}
    </div>
</div>
""", unsafe_allow_html=True)

# 圖表區 (兩欄佈局)
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    if df_intra is not None and not df_intra.empty:
        st.plotly_chart(plot_intraday_line(df_intra), use_container_width=True)
    else:
        st.warning("⚠️ 無法取得即時分時圖 (API 限制或盤前)")
        st.caption("提示：分時圖使用 Yahoo 數據，每 5 分鐘更新一次以避免封鎖。")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    if not df_daily.empty:
        st.plotly_chart(plot_daily_k(df_daily), use_container_width=True)
    else:
        st.error("無法取得歷史 K 線資料")
    st.markdown('</div>', unsafe_allow_html=True)

# 頁腳
update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f'<div class="footer">更新時間：{update_time}</div>', unsafe_allow_html=True)
