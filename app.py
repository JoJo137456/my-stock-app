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
        line=dict(color='#cbd5e1', width=2, dash='dash'), name=bench_name
    ))
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
    option = st.radio("監控標的", list(options_dict.keys()))
    code = options_dict[option] # === 這裡定義了 code ===
    
    is_tw_stock = code.isdigit()
    is_tw_index = (code == "^TWII")
    is_us_index = (code in ["^GSPC", "^VIX", "^TNX"])
    is_crypto = ("BTC" in code)
    is_forex = ("=X" in code or "DX" in code)
    is_futures = ("=F" in code)
    
    is_us_stock = not (is_tw_stock or is_tw_index or is_us_index or is_crypto or is_forex or is_futures)
    
    if is_tw_stock or is_tw_index or code == "TWD=X": market_type = 'TW'
    elif is_crypto: market_type = 'CRYPTO'
    else: market_type = 'US'
    
    st.divider()
    status_code, status_text = check_market_status(market_type=market_type)
    st.info(f"市場狀態：{status_text}")
    if is_us_stock and len(code) > 4: st.caption("註：本標的為 ADR (美國存託憑證)，走勢具母國連動性。")
    if st.button("🔄 同步最新報價"):
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
if not df_daily.empty and not (is_tw_index or code == "^GSPC"):
    bench_code = "^TWII" if is_tw_stock else "^GSPC"
    bench_name = "TAIEX (台灣加權指數)" if is_tw_stock else "S&P 500 指數"
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

# === 6. UI 呈現 ===
bg_color = "#f8fafc"
font_color = "#dc2626" if change >= 0 else "#16a34a" 
border_color = "#fca5a5" if change >= 0 else "#86efac"

currency_symbol = "NT$" if (is_tw_stock or is_tw_index or code == "TWD=X") else "$"
unit_label = "Pts" if (is_tw_index or is_us_index or code == "DX-Y.NYB") else \
             "/ oz" if (is_futures and ("GC" in code or "SI" in code)) else \
             "/ bbl" if (is_futures and "CL" in code) else \
             "%" if code == "^TNX" else ""

st.markdown(f"""
<div style="background-color: {bg_color}; padding: 25px; border-radius: 8px; margin-bottom: 25px; border-left: 6px solid {border_color};">
    <h2 style="margin:0; color:#475569; font-size: 1.1rem; font-weight: 600;">{option}</h2>
    <div style="display: flex; align-items: baseline; gap: 15px; margin-top: 8px;">
        <span style="font-size: 3.2rem; font-weight: 700; color: #0f172a; letter-spacing: -1px;">
           {currency_symbol.replace('NT$', '') if code != '^TNX' else ''} {current_price:,.2f} <span style="font-size: 1rem; color:#64748b; font-weight: 400;">{unit_label}</span>
        </span>
        <span style="font-size: 1.5rem; font-weight: 600; color: {font_color};">
             {change:+.2f} ({pct:+.2f}%)
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

hide_volume = (is_tw_index or is_us_index or is_forex)
safe_fmt = lambda x: f"{x:,.2f}" if isinstance(x, (int, float)) else x

if hide_volume:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("開盤價 (Open)", safe_fmt(real_data.get('open')))
    c2.metric("最高價 (High)", safe_fmt(real_data.get('high')))
    c3.metric("最低價 (Low)", safe_fmt(real_data.get('low')))
    c4.metric("前日收盤 (Prev Close)", f"{prev_close:,.2f}")
else:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("開盤價 (Open)", safe_fmt(real_data.get('open')))
    c2.metric("最高價 (High)", safe_fmt(real_data.get('high')))
    c3.metric("最低價 (Low)", safe_fmt(real_data.get('low')))
    c4.metric("前日收盤 (Prev Close)", f"{prev_close:,.2f}")
    vol_label = "成交量 (張)" if is_tw_stock else "成交量 (Volume)"
    c5.metric(vol_label, real_data.get('volume', '-'))

st.divider()

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
        st.error("暫無歷史交易資料")
    st.markdown('</div>', unsafe_allow_html=True)

if not df_bench.empty and not df_daily.empty:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    rs_fig = plot_relative_strength(df_daily, df_bench, option.split(" ")[-1], bench_name)
    if rs_fig:
        st.plotly_chart(rs_fig, use_container_width=True)
        st.caption("🔍 **分析備註**：將雙邊起漲點設為 100 基準化。當資產曲線（藍）凌駕於大盤曲線（灰）之上，表彰該資產具備超越大盤之動能（Alpha）；反之則顯示營運護城河面臨防禦壓力。")
    st.markdown('</div>', unsafe_allow_html=True)

# === 7. 高階幕僚戰略解讀 (確保放在 code 定義之後) ===
strategic_commentary = {
    "^VIX": {
        "title": "系統性風險與市場波動率指標 (VIX)",
        "business_model": "衡量總體經濟避險情緒與流動性壓力的關鍵指標，直接關聯集團資本運作的外部環境風險。",
        "high": "🔴 【風險溢酬升溫】代表市場流動性趨緊。建議啟動防禦機制，暫緩非必要之資本支出（CapEx），並重新檢視短期債務延展風險，以保護集團現金流。",
        "low": "🟢 【市場情緒穩定】資金承擔風險意願高。有利於集團旗下事業體（如遠東新、遠傳）向金融機構取得具競爭力之長期融資，亦為活化資產或戰略佈局之契機。"
    },
    "^TNX": {
        "title": "實質借貸成本與無風險利率 (U.S. 10Y Treasury)",
        "business_model": "全球資本市場之定價錨點，直接影響集團發債成本與長期投資計畫之折現率（WACC）評估。",
        "high": "🔴 【資金成本攀升】高度資本密集事業群（如不動產、大型擴廠）需嚴控利息保障倍數；惟集團具穩健現金流之傳產事業，相對具備抗震的防禦價值。",
        "low": "🟢 【融資環境寬鬆】利於集團以較低之資金成本進行舉債經營（Financial Leverage），加速推展亞泥、遠東新等指標性綠色轉型與大型資本支出案。"
    },
    "CT=F": {
        "title": "紡織事業群上游成本指標 (Cotton Futures)",
        "business_model": "牽動遠東新（1402）與宏遠（1460）紡織事業板塊之核心進貨成本與毛利率（Gross Margin）表現。",
        "high": "🔴 【進貨成本通膨】考驗集團對下游品牌端（如 Nike, UA）之議價與成本轉嫁能力（Pricing Power）；若轉嫁滯後，恐短期壓縮營業利益率。",
        "low": "🟢 【原物料壓力緩解】在終端消費需求維持平穩之假設下，成本下行將直接挹注紡織產品線之毛利率擴張，提升整體板塊之獲利動能。"
    },
    "CL=F": {
        "title": "化纖事業群核心原料指標 (WTI Crude Oil)",
        "business_model": "石油衍生品（如 PTA、MEG）為集團化纖板塊之基石。油價波動直接決定石化產品之報價結構與利差空間。",
        "high": "🔴 【石化原料上漲】推升進貨成本。若伴隨總體需求強勁，可推升終端產品報價；然若屬停滯性通膨，則將侵蝕東聯（1710）、遠東新化纖部門之獲利空間。",
        "low": "🟢 【生產成本減輕】有效降低化學纖維生產負擔。惟須同步檢視是否隱含全球製造業終端需求萎縮之衰退風險。"
    },
    "BDRY": {
        "title": "散裝航運景氣與運價指標 (BDRY Proxy)",
        "business_model": "反映全球鐵礦砂、煤炭等大宗物資之海運需求，為研判裕民航運（2606）本業獲利動能之領先指標。",
        "high": "🟢 【運力供不應求】現貨船運價揚升，將直接挹注裕民航運之營收規模與營業利益率，為集團貢獻顯著之現金流。",
        "low": "🔴 【運力過剩或需求疲軟】航運事業群之獲利貢獻預期應相應下修，戰略上需強化長約（Time Charter）比重以穩定業績基期。"
    },
    "TWD=X": {
        "title": "匯率曝險與外銷競爭力 (USD/TWD)",
        "business_model": "集團跨國營運與外銷佔比高，新台幣匯率波動直接影響合併財報之營收認列與業外損益（匯兌損益）。",
        "high": "🟢 【台幣貶值】有利於推升外銷產品之報價競爭力。同時，持有的美元計價資產與應收帳款將於財報上產生具體之匯兌收益（FX Gains）。",
        "low": "🔴 【台幣升值】削弱出口報價優勢。財務部門需審慎執行遠期外匯等避險（Hedging）操作，以對沖潛在之匯兌損失風險。"
    }
}

if code in strategic_commentary:
    st.markdown("### 🧠 總裁辦公室戰略分析 (Executive Summary)")
    info = strategic_commentary[code]
    st.markdown(f"""
    <div style="background-color: #ffffff; padding: 25px; border-radius: 8px; border-left: 5px solid #0f172a; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        <h4 style="margin-top: 0; color: #1e293b; font-size: 1.1rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">{info['title']}</h4>
        <p style="color: #475569; font-size: 0.95rem; margin-top: 15px; line-height: 1.6;"><strong>核心業務關聯：</strong>{info['business_model']}</p>
        <div style="display: flex; gap: 20px; margin-top: 15px;">
            <div style="flex: 1; background: #fef2f2; padding: 18px; border-radius: 6px; border: 1px solid #fecaca;">
                <p style="margin: 0; font-size: 0.92rem; color: #991b1b; line-height: 1.6;">{info['high']}</p>
            </div>
            <div style="flex: 1; background: #f0fdf4; padding: 18px; border-radius: 6px; border: 1px solid #bbf7d0;">
                <p style="margin: 0; font-size: 0.92rem; color: #166534; line-height: 1.6;">{info['low']}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f'<div class="footer">系統更新時間：{update_time} ｜ 資料來源：TWSE, Yahoo Finance</div>', unsafe_allow_html=True)
