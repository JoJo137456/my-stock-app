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
st.set_page_config(page_title="遠東集團_高階戰略戰情室", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei') 

# CSS 美化 (使用極簡專業風格)
st.markdown("""
    <style>
        html, body, [class*="css"]  { font-family: 'Microsoft JhengHei', 'Segoe UI', sans-serif !important; }
        .main-title { font-size: 2.2rem; font-weight: 700; color: #1e293b; text-align: center; margin: 1rem 0; letter-spacing: 1px;}
        .sub-title { font-size: 1rem; color: #64748b; text-align: center; margin-bottom: 2rem; }
        .chart-container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; border: 1px solid #e2e8f0; }
        .footer { text-align: center; color: #94a3b8; font-size: 0.8rem; margin-top: 3rem; }
        div[data-testid="metric-container"] {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">遠東集團 (Far Eastern Group)</div><div class="sub-title">聯合稽核總部 ｜ 戰略決策儀表板</div>', unsafe_allow_html=True)

# === 2. 核心功能模組 ===

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

# === 3. 繪圖模組 ===

def plot_daily_k(df):
    if df.empty: return None
    df = df.copy()
    df['Date'] = pd.to_datetime(df['date'])
    df.set_index('Date', inplace=True)
    df = df.tail(120)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#ef4444', increasing_fillcolor='#ef4444',
        decreasing_line_color='#22c55e', decreasing_fillcolor='#22c55e',
        name="日K"
    )])
    fig.update_layout(
        title="<b>📊 歷史價格走勢 (近半年)</b>",
        xaxis_rangeslider_visible=False,
        height=350,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#f1f5f9')
    )
    return fig

def plot_intraday_line(df):
    if df is None or df.empty: return None
    interval_str = "1 Min" if (df.index[1] - df.index[0]).seconds == 60 else "5 Min"
    y_min, y_max = df['Close'].min(), df['Close'].max()
    padding = (y_max - y_min) * 0.1 if y_max != y_min else y_max * 0.01
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'], mode='lines',
        line=dict(color='#0f172a', width=2.5),
        fill='tozeroy', fillcolor='rgba(15, 23, 42, 0.05)', name='報價'
    ))
    fig.add_hline(y=df['Open'].iloc[0], line_dash="dot", line_color="#94a3b8", annotation_text="開盤基準")
    fig.update_layout(
        title=f"<b>⚡ 當日分時動態 ({interval_str})</b>",
        height=350,
        margin=dict(l=10, r=10, t=40, b=10),
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(tickformat='%H:%M', showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#f1f5f9', tickformat='.2f', range=[y_min - padding, y_max + padding]) 
    )
    return fig

def plot_relative_strength(df_target, df_bench, target_name, bench_name):
    if df_target.empty or df_bench.empty: return None
    
    # 整理資料並取近 60 個交易日 (一季)
    df1 = df_target[['date', 'close']].tail(60).copy()
    df2 = df_bench[['date', 'close']].tail(60).copy()
    
    merged = pd.merge(df1, df2, on='date', suffixes=('_target', '_bench'), how='inner')
    if merged.empty: return None
    
    base_target = merged['close_target'].iloc[0]
    base_bench = merged['close_bench'].iloc[0]
    merged['Target_Norm'] = (merged['close_target'] / base_target) * 100
    merged['Bench_Norm'] = (merged['close_bench'] / base_bench) * 100
    
    fig = go.Figure()
    # 大盤線 (防禦基準線)
    fig.add_trace(go.Scatter(
        x=merged['date'], y=merged['Bench_Norm'], mode='lines',
        line=dict(color='#cbd5e1', width=2, dash='dash'), name=bench_name
    ))
    # 個股線
    fig.add_trace(go.Scatter(
        x=merged['date'], y=merged['Target_Norm'], mode='lines',
        line=dict(color='#2563eb', width=3), name=target_name
    ))
    
    fig.update_layout(
        title="<b>🛡️ 戰略雷達：相對強勢分析 (一季基準化 Base=100)</b>",
        height=350,
        margin=dict(l=10, r=10, t=40, b=10),
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#f1f5f9', title="累積報酬指數")
    )
    return fig

# === 4. 主控台邏輯 ===
market_categories = {
    "📈 總體經濟與大盤 (宏觀與風險指標)": {
        "🇹🇼 台灣加權指數 (TAIEX)": "^TWII",
        "🇺🇸 S&P 500 (標普500)": "^GSPC",
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
    st.header("🎯 戰略監控目標")
    selected_category = st.selectbox("板塊分類", list(market_categories.keys()))
    st.markdown("---")
    
    options_dict = market_categories[selected_category]
    option = st.
