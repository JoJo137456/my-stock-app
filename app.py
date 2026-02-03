import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime
import pytz

# === 1. 系統設定與 CSS 優化 ===
st.set_page_config(page_title="遠東集團戰情室", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

# CSS: 強制放大字體，模擬財經網站排版
st.markdown("""
    <style>
        html, body, [class*="css"] { font-family: 'Microsoft JhengHei', sans-serif !important; }
        
        /* 放大 Metric (股價大數字) */
        div[data-testid="stMetricValue"] { font-size: 2.5rem !important; font-weight: 700; }
        div[data-testid="stMetricDelta"] { font-size: 1.1rem !important; }
        div[data-testid="stMetricLabel"] { font-size: 1.1rem !important; color: #555; }
        
        /* 讓圖表更緊湊 */
        div[data-testid="stAltairChart"] { margin-top: -20px; }
        
        /* 表格樣式 */
        div[data-testid="stDataFrame"] { font-size: 1.1rem !important; }
    </style>
""", unsafe_allow_html=True)

# === 2. 數據獲取邏輯 (修復序列化錯誤) ===

STOCK_LIST = {
    "1402 遠東新": "1402.TW", "1102 亞泥": "1102.TW", "2606 裕民": "2606.TW",
    "1460 宏遠": "1460.TW", "2903 遠百": "2903.TW", "4904 遠傳": "4904.TW", "1710 東聯": "1710.TW"
}

@st.cache_data(ttl=60)
def get_group_summary():
    """一次獲取所有股票的當下行情，製作頂部列表"""
    summary_data = []
    tickers = " ".join(STOCK_LIST.values())
    try:
        # 為了速度，先用 download 抓大概，再用 Ticker 補強
        # 這裡直接迴圈抓 Ticker 因為我們要準確的 last_price
        for name, symbol in STOCK_LIST.items():
            try:
                t = yf.Ticker(symbol)
                fi = t.fast_info
                curr = fi.last_price
                prev = fi.previous_close
                if curr and prev:
                    change = curr - prev
                    pct = (change / prev) * 100
                    summary_data.append({
                        "代號": symbol.replace(".TW", ""),
                        "名稱": name.split(" ")[1],
                        "現價": curr,
                        "漲跌": change,
                        "幅度(%)": pct,
                        "昨收": prev
                    })
            except:
                continue
        return pd.DataFrame(summary_data)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=30)
def get_market_and_stock_detail(stock_symbol):
    """同時抓取大盤與個股資料"""
    try:
        # 1. 大盤 (TWII)
        twii = yf.Ticker("^TWII")
        twii_fi = twii.fast_info
        twii_data = {
            "current": twii_fi.last_price,
            "prev_close": twii_fi.previous_close,
            "day_high": twii_fi.day_high,
            "day_low": twii_fi.day_low,
            "volume": twii_fi.last_volume
        }

        # 2. 個股
        stock = yf.Ticker(stock_symbol)
        df = stock.history(period="1d", interval="1m", auto_adjust=False)
        fi = stock.fast_info
        
        # 轉換 FastInfo 為字典 (關鍵修復)
        stock_info = {
            "last_price": fi.last_price,
            "previous_close": fi.previous_close,
            "open": fi.open,
            "day_high": fi.day_high,
            "day_low": fi.day_low,
            "last_volume": fi.last_volume
        }
        
        return {
            "twii": twii_data,
            "stock_info": stock_info,
            "stock_df": df
        }
    except:
        return None

# === 3. 繪圖引擎 (Yahoo 風格：線圖 + 成交量) ===

def draw_yahoo_combo_chart(df, prev_close):
    if df.empty: return None
    
    df = df.reset_index()
    # 欄位統一
    time_col = "Date" if "Date" in df.columns else "Datetime"
    if time_col in df.columns: df.rename(columns={time_col: "Time"}, inplace=True)
    
    # 時區
    if df['Time'].dt.tz is None:
        df['Time'] = df['Time'].dt.tz_localize('UTC').dt.tz_convert(tw_tz)
    else:
        df['Time'] = df['Time'].dt.tz_convert(tw_tz)

    # --- 顏色邏輯 ---
    # 股價圖顏色：根據「現在價格 vs 昨收」決定整條線顏色
    current_price = df['Close'].iloc[-1]
    is_up = current_price >= prev_close
    main_color = "#d62728" if is_up else "#009900" # 紅漲綠跌 (Yahoo 色系)

    # 成交量顏色：根據「K棒漲跌 (收>開)」決定單根顏色
    # 若沒有 Open 數據，就跟前一分鐘比
    if 'Open' in df.columns:
        df['VolColor'] = df.apply(lambda x: '#d62728' if x['Close'] >= x['Open'] else '#009900', axis=1)
    else:
        df['VolColor'] = main_color

    # --- Y軸範圍 (斜率關鍵) ---
    # 必須包含「昨收」與「今日高低」，並給予緩衝，才能看出波動
    y_min = min(df['Low'].min(), prev_close)
    y_max = max(df['High'].max(), prev_close)
    padding = (y_max - y_min) * 0.05 if y_max != y_min else y_max * 0.01
    y_domain = [y_min - padding, y_max + padding]

    # --- 共用 X 軸 ---
    base = alt.Chart(df).encode(
        x=alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M', grid=True, tickCount=6))
    )

    # --- 圖表 1: 股價走勢 (Line + Area + Rule) ---
    # 區域漸層
    area = base.mark_area(opacity=0.1, color=main_color).encode(
        y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain), axis=alt.Axis(title='股價'))
    )
    # 線條
    line = base.mark_line(strokeWidth=2.5, color=main_color).encode(
        y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain))
    )
    # 昨收基準線 (0% 線)
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(
        strokeDash=[5, 5], size=1.5, color='#888'
    ).encode(y='y')

    price_chart = (area + line + rule).properties(height=350)

    # --- 圖表 2: 成交量 (Bar) ---
    vol_chart = base.mark_bar().encode(
        y=alt.Y('Volume:Q', axis=alt.Axis(title='成交量', tickCount=3)),
        color=alt.Color('VolColor:N', scale=None),
        tooltip=['Time', 'Close', 'Volume']
    ).properties(height=100)

    # 垂直合併
    return alt.vconcat(price_chart, vol_chart, spacing=0).resolve_scale(x='shared')

# === 4. 主程式介面 ===

# --- A. 頂部：遠東集團總表 ---
st.subheader("📊 遠東集團戰情看板")
df_summary = get_group_summary()

if not df_summary.empty:
    def color_map(val):
        if val > 0: return 'color: #d62728' # Red
        elif val < 0: return 'color: #009900' # Green
        return 'color: gray'

    st.dataframe(
        df_summary.style.map(color_map, subset=['漲跌', '幅度(%)'])
                  .format({"現價": "{:.2f}", "漲跌": "{:+.2f}", "幅度(%)": "{:+.2f}%", "昨收": "{:.2f}"}),
        hide_index=True,
        use_container_width=True,
        height=250
    )
else:
    st.info("連線中... 正在獲取集團數據")

st.markdown("---")

# --- B. 核心戰情室 (左：大盤 / 右：個股) ---
col_idx, col_stock = st.columns([1.2, 3])

# 先選擇個股，以便抓取資料
with col_stock:
    # 隱藏式選單
    selected_name = st.radio("監控標的", list(STOCK_LIST.keys()), horizontal=True, label_visibility="collapsed")
    ticker = STOCK_LIST[selected_name]

# 抓取所有資料
data = get_market_and_stock_detail(ticker)

# 左側：大盤
with col_idx:
    st.markdown("### 🇹🇼 加權指數")
    if data and data['twii']['current']:
        t_info = data['twii']
        t_change = t_info['current'] - t_info['prev_close']
        t_pct = (t_change / t_info['prev_close']) * 100
        
        st.metric("加權指數", f"{t_info['current']:,.0f}", f"{t_change:+.0f} ({t_pct:+.2f}%)")
        
        st.markdown(f"""
        <div style="color: #555; font-size: 1rem; line-height: 1.8;">
        <b>成交量:</b> {t_info['volume']/1000000:.0f} M<br>
        <b>最高:</b> {t_info['day_high']:,.0f}<br>
        <b>最低:</b> {t_info['day_low']:,.0f}<br>
        <b>昨收:</b> {t_info['prev_close']:,.0f}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("大盤資料讀取中...")

# 右側：個股詳細
with col_stock:
    if data and data['stock_info']['last_price']:
        s_info = data['stock_info']
        s_curr = s_info['last_price']
        s_prev = s_info['previous_close']
        
        if s_prev is None: s_prev = s_curr # 防呆
        
        s_change = s_curr - s_prev
        s_pct = (s_change / s_prev) * 100
        
        # Yahoo 風格 Header
        color_css = "#d62728" if s_change > 0 else "#009900"
        arrow = "▲" if s_change > 0 else "▼"
        if s_change == 0: color_css, arrow = "gray", "-"
        
        # 顯示大標題
        st.markdown(f"""
        <div style="display: flex; align-items: baseline; gap: 15px; margin-bottom: 10px;">
            <span style="font-size: 2.2rem; font-weight: bold;">{selected_name}</span>
            <span style="font-size: 3rem; font-weight: bold;">{s_curr:.2f}</span>
            <span style="color: {color_css}; font-size: 2rem; font-weight: bold;">
                {arrow} {abs(s_change):.2f} ({s_pct:+.2f}%)
            </span>
            <span style="color: #666; font-size: 1.2rem; margin-left: auto;">
                成交量: {s_info['last_volume']/1000:,.0f} 張
            </span>
        </div>
        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; display: flex; gap: 20px; font-size: 1.1rem;">
            <span>開盤: <b>{s_info['open']:.2f}</b></span>
            <span>最高: <b>{s_info['day_high']:.2f}</b></span>
            <span>最低: <b>{s_info['day_low']:.2f}</b></span>
            <span>昨收: <b>{s_prev:.2f}</b></span>
        </div>
        """, unsafe_allow_html=True)
        
        # 繪製圖表
        if not data['stock_df'].empty:
            chart = draw_yahoo_combo_chart(data['stock_df'], s_prev)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Yahoo Finance 盤中資料尚未更新，請稍候...")
    else:
        st.error("無法取得個股資料，請確認代號或網路連線。")

st.markdown(f"<div style='text-align: right; color: #ccc; margin-top: 20px;'>戰情中心 | 更新時間: {datetime.now(tw_tz).strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
